from decimal import Decimal
from types import SimpleNamespace

import pytest
from kombu.exceptions import OperationalError  # type: ignore[import-untyped]
from redis import RedisError

import app.usecases.transfers as transfers_usecase
from app.db.models import Transaction, User, Wallet
from app.idempotency import IdempotencyManager, hash_payload
from app.services.exceptions import (
    BadRequest,
    Conflict,
    IdempotencyKeyConflict,
    NotFound,
    RequestInProgress,
)
from app.services.transfers import create_transfer
from app.usecases.transfers import create_transfer_idempotent


def test_post_transfer_side_effects_logs_broker_error(
    monkeypatch,
    caplog,
):
    transfer = SimpleNamespace(id=7, from_wallet_id=1, to_wallet_id=2)
    db = SimpleNamespace(get=lambda *_args: SimpleNamespace(user_id=3))

    monkeypatch.setattr(transfers_usecase, "invalidate_wallet_cache", lambda *_: None)

    def broker_unavailable(*_args):
        raise OperationalError("broker unavailable")

    monkeypatch.setattr(
        transfers_usecase,
        "enqueue_transfer_notification",
        broker_unavailable,
    )

    with caplog.at_level("ERROR"):
        transfers_usecase._post_transfer_side_effects(db, transfer, "fingerprint")

    record = next(
        record
        for record in caplog.records
        if record.message == "transfer_notification_enqueue_failed"
    )
    assert record.exc_info is not None
    assert record.exc_info[0] is OperationalError
    assert str(record.exc_info[1]) == "broker unavailable"


def test_post_transfer_side_effects_does_not_hide_programming_error(monkeypatch):
    transfer = SimpleNamespace(id=7, from_wallet_id=1, to_wallet_id=2)
    db = SimpleNamespace(get=lambda *_args: SimpleNamespace(user_id=3))

    monkeypatch.setattr(transfers_usecase, "invalidate_wallet_cache", lambda *_: None)

    def programming_error(*_args):
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(
        transfers_usecase,
        "enqueue_transfer_notification",
        programming_error,
    )

    with pytest.raises(RuntimeError, match="unexpected bug"):
        transfers_usecase._post_transfer_side_effects(db, transfer, "fingerprint")


def _mk_user_and_wallet(db, balance: Decimal) -> Wallet:
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = Wallet(user_id=user.id, balance=balance)
    db.add(wallet)
    db.commit()
    return wallet


def test_transfer_success(db):
    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    tx = create_transfer(db, from_w.id, to_w.id, Decimal("25.50"))

    db.refresh(from_w)
    db.refresh(to_w)

    assert isinstance(tx, Transaction)
    assert tx.from_wallet_id == from_w.id
    assert tx.to_wallet_id == to_w.id
    assert tx.amount == Decimal("25.50")
    assert from_w.balance == Decimal("74.50")
    assert to_w.balance == Decimal("25.50")


def test_transfer_same_wallet_bad_request(db):
    w = _mk_user_and_wallet(db, Decimal("100.00"))

    with pytest.raises(BadRequest):
        create_transfer(db, w.id, w.id, Decimal("10.00"))


def test_transfer_amount_none_bad_request(db):
    w1 = _mk_user_and_wallet(db, Decimal("100.00"))
    w2 = _mk_user_and_wallet(db, Decimal("0.00"))

    with pytest.raises(BadRequest):
        create_transfer(db, w1.id, w2.id, None)  # type: ignore[arg-type]


def test_transfer_amount_zero_or_negative_bad_request(db):
    w1 = _mk_user_and_wallet(db, Decimal("100.00"))
    w2 = _mk_user_and_wallet(db, Decimal("0.00"))

    with pytest.raises(BadRequest):
        create_transfer(db, w1.id, w2.id, Decimal("0"))

    with pytest.raises(BadRequest):
        create_transfer(db, w1.id, w2.id, Decimal("-1"))


def test_transfer_from_wallet_not_found(db):
    w2 = _mk_user_and_wallet(db, Decimal("0.00"))

    with pytest.raises(NotFound):
        create_transfer(db, 999999, w2.id, Decimal("10.00"))


def test_transfer_to_wallet_not_found(db):
    w1 = _mk_user_and_wallet(db, Decimal("100.00"))

    with pytest.raises(NotFound):
        create_transfer(db, w1.id, 999999, Decimal("10.00"))


def test_transfer_insufficient_funds_conflict_and_atomic(db):
    from_w = _mk_user_and_wallet(db, Decimal("5.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    before_from = from_w.balance
    before_to = to_w.balance

    with pytest.raises(Conflict):
        create_transfer(db, from_w.id, to_w.id, Decimal("10.00"))

    db.refresh(from_w)
    db.refresh(to_w)

    assert from_w.balance == before_from
    assert to_w.balance == before_to
    assert db.query(Transaction).count() == 0


def test_idempotent_transfer_redis_same_key_raises_in_progress_without_double_debit(
    monkeypatch, db, fake_redis
):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    tx1 = create_transfer_idempotent(
        db, from_w.id, to_w.id, Decimal("10.00"), "redis-1"
    )
    with pytest.raises(RequestInProgress):
        create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "redis-1")

    db.refresh(from_w)
    db.refresh(to_w)

    assert tx1.id is not None
    assert from_w.balance == Decimal("90.00")
    assert to_w.balance == Decimal("10.00")


def test_idempotent_transfer_redis_writes_request_hash(monkeypatch, db, fake_redis):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "redis-done")

    raw = fake_redis.get("idem:transfer:redis-done")
    assert raw is not None

    payload = {"from_wallet_id": from_w.id, "to_wallet_id": to_w.id, "amount": "10.00"}
    assert raw.decode("utf-8") == hash_payload(payload)


def test_idempotent_transfer_redis_conflict_by_payload(monkeypatch, db, fake_redis):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "redis-2")

    with pytest.raises(IdempotencyKeyConflict):
        create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("20.00"), "redis-2")


def test_idempotent_transfer_existing_same_hash_raises_in_progress(
    monkeypatch, db, fake_redis
):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    fake_redis.set(
        "idem:transfer:redis-processing",
        "same-hash",
    )

    monkeypatch.setattr(
        "app.usecases.transfers.hash_payload",
        lambda *_args, **_kwargs: "same-hash",
    )

    with pytest.raises(RequestInProgress):
        create_transfer_idempotent(
            db, from_w.id, to_w.id, Decimal("5.00"), "redis-processing"
        )


def test_idempotent_transfer_without_redis_raises_in_progress(monkeypatch, db):
    # Null Object pattern case
    monkeypatch.setattr(
        transfers_usecase, "get_idempotency_manager", lambda: IdempotencyManager(None)
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    with pytest.raises(RequestInProgress):
        create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("5.00"), "no-redis")


def test_idempotent_transfer_redis_error_raises_in_progress(monkeypatch, db):
    class FailingRedis:
        def get(self, *args, **kwargs):
            raise RedisError("error")

        def set(self, *args, **kwargs):
            raise RedisError("error")

        def delete(self, *args, **kwargs):
            raise RedisError("error")

    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(FailingRedis()),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    with pytest.raises(RequestInProgress):
        create_transfer_idempotent(
            db, from_w.id, to_w.id, Decimal("5.00"), "redis-fail-1"
        )


def test_idempotent_transfer_error_cleanup_deletes_processing_key(
    monkeypatch, db, fake_redis
):
    monkeypatch.setattr(
        transfers_usecase,
        "get_idempotency_manager",
        lambda: IdempotencyManager(fake_redis),
    )

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(transfers_usecase, "create_transfer", boom)

    with pytest.raises(RuntimeError):
        create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("5.00"), "cleanup-1")

    assert fake_redis.get("idem:transfer:cleanup-1") is None
