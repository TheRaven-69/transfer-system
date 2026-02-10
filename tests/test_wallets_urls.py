from datetime import datetime
from decimal import Decimal

import app.api.wallets as wallets_router


class DummyUser:
    def __init__(self, id: int):
        self.id = id
        self.created_at = datetime(2026, 2, 7, 12, 0, 0)


class DummyWallet:
    def __init__(self, id: int ,user_id: int, balance: str):
        self.id = id
        self.user_id = user_id
        self.balance = Decimal(balance)
        self.user = DummyUser(user_id)



def test_post_wallets_auto_create_returns_wallet_and_user(client, monkeypatch):
    def fake_create_wallet_with_autouser(db):
        return DummyWallet(id=1, user_id=10, balance="0")

    monkeypatch.setattr(wallets_router, "create_wallet_with_autouser", fake_create_wallet_with_autouser)

    r = client.post("/wallets")
    assert r.status_code == 200

    data = r.json()
    assert "wallet" in data
    assert "user" in data

    assert data["wallet"]["id"] == 1
    assert data["wallet"]["user_id"] == 10
    assert data["wallet"]["balance"] is not None

    assert data["user"]["id"] == 10
    assert data["user"]["created_at"] is not None


def test_get_wallet_by_id_returns_wallet(client, monkeypatch):
    def fake_get_wallet(db, wallet_id: int):
        return DummyWallet(id=wallet_id, user_id=99, balance="123.45")

    monkeypatch.setattr(wallets_router, "get_wallet", fake_get_wallet)

    r = client.get("/wallets/5")
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 5
    assert data["user_id"] == 99
    assert data["balance"] is not None


def test_get_wallet_not_found_returns_404(client, monkeypatch):
    # Якщо в майбутньому сервіс буде кидати HTTPException(404)
    from fastapi import HTTPException

    def fake_get_wallet(db, wallet_id: int):
        raise HTTPException(status_code=404, detail="Wallet not found")

    monkeypatch.setattr(wallets_router, "get_wallet", fake_get_wallet)

    r = client.get("/wallets/999999")
    assert r.status_code == 404
