from datetime import datetime
from decimal import Decimal

import app.api.users as users_router


class DummyUser:
    def __init__(self, id: int, wallet: "DummyWallet", name: str = "Test"):
        self.id = id
        self.name = name
        self.username = name.casefold()
        self.email = f"{name.casefold()}@example.com"
        self.wallet = wallet
        self.created_at = datetime(2026, 2, 7, 12, 0, 0)


class DummyWallet:
    def __init__(self, id: int, user_id: int, balance: str):
        self.id = id
        self.user_id = user_id
        self.balance = Decimal(balance)


def test_post_users_is_replaced_by_auth_registration(client):
    assert client.post("/users").status_code == 404


def test_get_user_returns_user(client, monkeypatch, auth_user, auth_headers):
    def fake_get_user_by_id(db, user_id: int):
        return DummyUser(
            id=user_id,
            wallet=DummyWallet(id=77, user_id=user_id, balance="50.00"),
            name="Alice",
        )

    monkeypatch.setattr(users_router, "get_user_by_id", fake_get_user_by_id)

    r = client.get(f"/users/{auth_user.id}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == auth_user.id
    assert data["wallet"]["id"] == 77
    assert data["wallet"]["balance"] is not None
