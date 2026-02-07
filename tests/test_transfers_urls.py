from datetime import datetime
from decimal import Decimal

import app.api.transfers as transfers_router  


class DummyTransfer:
    def __init__(self, id: int, from_wallet_id: int, to_wallet_id: int, amount: str):
        self.id = id
        self.from_wallet_id = from_wallet_id
        self.to_wallet_id = to_wallet_id
        self.amount = Decimal(amount)
        self.created_at = datetime(2026, 2, 7, 12, 0, 0)


def test_post_transfers_creates_transfer(client, monkeypatch):
    def fake_create_transfer(db, from_wallet_id: int, to_wallet_id: int, amount):
        return DummyTransfer(id=1, from_wallet_id=from_wallet_id, to_wallet_id=to_wallet_id, amount=str(amount))


    monkeypatch.setattr(transfers_router, "create_transfer", fake_create_transfer)

    r = client.post(
        "/transfers",
        params={"from_wallet_id": 1, "to_wallet_id": 2, "amount": "25.5"},
    )
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 1
    assert data["from_wallet_id"] == 1
    assert data["to_wallet_id"] == 2
    assert data["amount"] is not None
    assert data["created_at"] is not None


def test_post_transfers_not_enough_money_returns_400(client, monkeypatch):
    from fastapi import HTTPException

    def fake_create_transfer(db, from_wallet_id: int, to_wallet_id: int, amount):
        raise HTTPException(status_code=400, detail="Not enough funds")

    monkeypatch.setattr(transfers_router, "create_transfer", fake_create_transfer)

    r = client.post(
        "/transfers",
        params={"from_wallet_id": 1, "to_wallet_id": 2, "amount": "9999"},
    )
    assert r.status_code == 400
