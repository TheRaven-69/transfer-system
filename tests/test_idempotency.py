from decimal import Decimal

from redis import RedisError
from sqlalchemy import func, select

import app.usecases.transfers as transfers_usecase
from app.db.models import Transaction, Wallet
from app.idempotency import IdempotencyManager


def test_reservation_cleanup_logs_redis_error_without_raw_key(caplog):
    class FailingRedis:
        def delete(self, *_args, **_kwargs):
            raise RedisError("cleanup unavailable")

    manager = IdempotencyManager(FailingRedis())  # type: ignore[arg-type]

    with caplog.at_level("WARNING"):
        manager.remove_reservation("transfer:raw-secret-key")

    record = next(
        record
        for record in caplog.records
        if record.message == "idempotency_reservation_cleanup_failed"
    )
    assert record.exc_info is not None
    assert record.exc_info[0] is RedisError
    assert str(record.exc_info[1]) == "cleanup unavailable"
    extra_fields = record.__dict__["extra_fields"]
    assert extra_fields["operation"] == "remove_reservation"
    assert "raw-secret-key" not in str(extra_fields)


def test_idempotency_same_key_returns_same_transaction_and_no_double_debit(
    client, db, seeded_wallets, monkeypatch, fake_redis
):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    w1, w2 = seeded_wallets
    headers = {"Idempotency-Key": "abc-123"}

    r1 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r2.status_code == 409
    assert r2.json() == {
        "detail": "A request is already in progress",
        "request_id": r2.headers["X-Request-ID"],
    }

    count = db.execute(select(func.count(Transaction.id))).scalar_one()
    assert count == 1

    from_wallet = db.get(Wallet, w1.id)
    to_wallet = db.get(Wallet, w2.id)
    assert from_wallet.balance == Decimal("990.00")
    assert to_wallet.balance == Decimal("10.00")


def test_idempotency_same_key_different_payload_conflict(
    client, seeded_wallets, monkeypatch, fake_redis
):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

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
    assert r2.json() == {
        "detail": "Idempotency-Key reuse with different request data",
        "request_id": r2.headers["X-Request-ID"],
    }


def test_idempotency_key_is_required(client, seeded_wallets):
    w1, w2 = seeded_wallets

    response = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers={"X-Request-ID": "validation-request"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation error",
        "request_id": "validation-request",
    }
