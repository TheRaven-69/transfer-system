from sqlalchemy import select

from app.db.models import RefreshToken, User

REGISTER_PAYLOAD = {
    "username": "Alice.User",
    "email": "Alice@Example.com",
    "password": "correct-horse-battery-staple",
}


def register(client, **overrides):
    payload = {**REGISTER_PAYLOAD, **overrides}
    return client.post("/auth/register", json=payload)


def login(client, identifier="alice.user", password=REGISTER_PAYLOAD["password"]):
    return client.post(
        "/auth/login",
        json={"identifier": identifier, "password": password},
    )


def test_register_creates_user_wallet_and_password_hash(client, db):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice.user"
    assert body["email"] == "alice@example.com"
    assert body["wallet"]["id"] is not None

    user = db.scalar(select(User).where(User.id == body["id"]))
    assert user is not None
    assert user.password_hash.startswith("scrypt$")
    assert REGISTER_PAYLOAD["password"] not in user.password_hash


def test_register_rejects_duplicate_username_and_email(client):
    assert register(client).status_code == 201

    duplicate_username = register(
        client,
        email="different@example.com",
    )
    assert duplicate_username.status_code == 409
    assert duplicate_username.json() == {"detail": "Username is already registered"}

    duplicate_email = register(
        client,
        username="different-user",
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.json() == {"detail": "Email is already registered"}


def test_login_accepts_username_or_email_and_sets_refresh_cookie(client):
    assert register(client).status_code == 201

    username_login = login(client, "ALICE.USER")
    assert username_login.status_code == 200
    assert username_login.json()["token_type"] == "bearer"
    assert username_login.json()["access_token"]
    assert client.cookies.get("refresh_token") is not None

    email_login = login(client, "ALICE@EXAMPLE.COM")
    assert email_login.status_code == 200
    assert email_login.json()["access_token"]


def test_login_uses_generic_error_for_unknown_user_or_wrong_password(client):
    assert register(client).status_code == 201

    wrong_password = login(client, password="wrong-password")
    unknown_user = login(client, identifier="missing-user")

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    expected = {"detail": "Invalid username, email, or password"}
    assert wrong_password.json() == expected
    assert unknown_user.json() == expected


def test_me_requires_access_token_and_returns_current_user(client):
    registered = register(client).json()
    access_token = login(client).json()["access_token"]

    assert client.get("/auth/me").status_code == 401

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]
    assert response.json()["username"] == "alice.user"


def test_refresh_rotates_token_and_rejects_reuse(client, db):
    assert register(client).status_code == 201
    assert login(client).status_code == 200
    old_refresh_token = client.cookies.get("refresh_token")

    refreshed = client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert client.cookies.get("refresh_token") != old_refresh_token

    old_record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash.is_not(None)).limit(1)
    )
    assert old_record is not None
    assert old_record.revoked_at is not None

    client.cookies.set("refresh_token", old_refresh_token, path="/auth")
    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token_and_clears_cookie(client):
    assert register(client).status_code == 201
    assert login(client).status_code == 200

    response = client.post("/auth/logout")
    assert response.status_code == 204
    assert client.cookies.get("refresh_token") is None
    assert client.post("/auth/refresh").status_code == 401


def test_user_cannot_access_another_users_profile(client):
    first_user = register(client).json()
    first_access_token = login(client).json()["access_token"]

    second_user = register(
        client,
        username="bob",
        email="bob@example.com",
        password="another-secure-password",
    ).json()

    response = client.get(
        f"/users/{second_user['id']}",
        headers={"Authorization": f"Bearer {first_access_token}"},
    )
    assert first_user["id"] != second_user["id"]
    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}


def test_user_cannot_transfer_from_another_users_wallet(client):
    first_user = register(client).json()
    first_access_token = login(client).json()["access_token"]
    second_user = register(
        client,
        username="bob",
        email="bob@example.com",
        password="another-secure-password",
    ).json()

    response = client.post(
        "/transfers",
        params={
            "from_wallet_id": second_user["wallet"]["id"],
            "to_wallet_id": first_user["wallet"]["id"],
            "amount": "1.00",
        },
        headers={
            "Authorization": f"Bearer {first_access_token}",
            "Idempotency-Key": "foreign-wallet-attempt",
        },
    )
    assert response.status_code == 403
