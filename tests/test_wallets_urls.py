from decimal import Decimal

import app.api.wallets as wallets_router


class DummyWallet:
    def __init__(self, id: int ,user_id: int, balance: str):
        self.id = id
        self.user_id = user_id
        self.balance = Decimal(balance)


def test_get_wallet_by_id_returns_wallet(client, monkeypatch):
    def fake_get_wallet_cached(db, wallet_id: int):
        return {"id": wallet_id, "user_id": 99, "balance": "123.45"}

    monkeypatch.setattr(wallets_router, "get_wallet_cached", fake_get_wallet_cached)

    r = client.get("/wallets/5")
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 5
    assert data["user_id"] == 99
    assert data["balance"] is not None


def test_get_wallet_not_found_returns_404(client, monkeypatch):
    from app.services.exceptions import WalletNotFound

    def fake_get_wallet_cached(db, wallet_id: int):
        raise WalletNotFound(wallet_id)

    monkeypatch.setattr(wallets_router, "get_wallet_cached", fake_get_wallet_cached)

    r = client.get("/wallets/999999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Wallet with id 999999 not found."}
