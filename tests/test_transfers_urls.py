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


def test_post_transfers_creates_transfer(client, monkeypatch, auth_user, auth_headers):
    def fake_create_transfer(
        db,
        from_wallet_id: int,
        to_wallet_id: int,
        amount,
        idempotency_key: str,
        actor_user_id: int | None = None,
    ):
        return DummyTransfer(
            id=1,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=str(amount),
        )

    monkeypatch.setattr(transfers_router, "create_transfer", fake_create_transfer)

    r = client.post(
        "/transfers",
        params={
            "from_wallet_id": auth_user.wallet.id,
            "to_wallet_id": 2,
            "amount": "25.5",
        },
        headers={**auth_headers, "Idempotency-Key": "url-test-1"},
    )
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 1
    assert data["from_wallet_id"] == 1
    assert data["to_wallet_id"] == 2
    assert data["amount"] is not None
    assert data["created_at"] is not None


def test_post_transfers_not_enough_money_returns_409(
    client, monkeypatch, auth_user, auth_headers
):
    from app.services.exceptions import InsufficientFunds

    def fake_create_transfer(
        db,
        from_wallet_id: int,
        to_wallet_id: int,
        amount,
        idempotency_key: str,
        actor_user_id: int | None = None,
    ):
        raise InsufficientFunds()

    monkeypatch.setattr(transfers_router, "create_transfer", fake_create_transfer)

    r = client.post(
        "/transfers",
        params={
            "from_wallet_id": auth_user.wallet.id,
            "to_wallet_id": 2,
            "amount": "9999",
        },
        headers={**auth_headers, "Idempotency-Key": "url-test-2"},
    )
    assert r.status_code == 409
    assert r.json() == {
        "detail": "Insufficient funds",
        "request_id": r.headers["X-Request-ID"],
    }
