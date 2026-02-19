from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import Transaction, Wallet
import app.services.transfers as transfers_service


def test_idempotency_same_key_returns_same_transaction_and_no_double_debit(client, db, seeded_wallets, monkeypatch, fake_redis):
    monkeypatch.setattr(transfers_service, "get_redis", lambda: fake_redis)

    w1, w2 = seeded_wallets
    headers = {"Idempotency-Key": "abc-123"}

    r1 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r1.status_code == 200
    tx1 = r1.json()

    r2 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r2.status_code == 409
    assert r2.json() == {"detail": "A request is already in progress"}

    count = db.execute(select(func.count(Transaction.id))).scalar_one()
    assert count == 1

    from_wallet = db.get(Wallet, w1.id)
    to_wallet = db.get(Wallet, w2.id)
    assert from_wallet.balance == Decimal("990.00")
    assert to_wallet.balance == Decimal("10.00")


def test_idempotency_same_key_different_payload_conflict(client, seeded_wallets, monkeypatch, fake_redis):
    monkeypatch.setattr(transfers_service, "get_redis", lambda: fake_redis)

    w1, w2 = seeded_wallets
    headers = {"Idempotency-Key": "abc-999"}

    r1 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "20.00"},
        headers=headers,
    )
    assert r2.status_code == 409
    assert r2.json() == {"detail": "Idempotency-Key reuse with different request data"}


def test_idempotency_key_is_required(client, seeded_wallets):
    w1, w2 = seeded_wallets

    response = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
    )

    assert response.status_code == 422
