from datetime import datetime
from decimal import Decimal
import app.api.users as users_router  


class DummyUser:
    def __init__(self, id: int, wallet: "DummyWallet", name: str = "Test"):
        self.id = id
        self.name = name
        self.wallet = wallet
        self.created_at = datetime(2026, 2, 7, 12, 0, 0)


class DummyWallet:
    def __init__(self, id: int, user_id: int, balance: str):
        self.id = id
        self.user_id = user_id
        self.balance = Decimal(balance)


def test_post_users_creates_user_and_wallet(client, monkeypatch):
    def fake_create_user(db, *args, **kwargs):
        return DummyUser(id=1, wallet=DummyWallet(id=11, user_id=1, balance="100.00"), name="John")


    monkeypatch.setattr(users_router, "create_user", fake_create_user)

    r = client.post("/users")
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 1
    assert data.get("created_at") is not None
    assert data["wallet"]["balance"] is not None
    assert "id" not in data["wallet"]


def test_get_user_returns_user(client, monkeypatch):
    def fake_get_user_by_id(db, user_id: int):
        return DummyUser(id=user_id, wallet=DummyWallet(id=77, user_id=user_id, balance="50.00"), name="Alice")

    monkeypatch.setattr(users_router, "get_user_by_id", fake_get_user_by_id)

    r = client.get("/users/7")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 7
    assert data["wallet"]["id"] == 77
    assert data["wallet"]["balance"] is not None
