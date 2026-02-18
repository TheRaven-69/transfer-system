from decimal import Decimal

import pytest
from redis import RedisError

from app.db.models import Transaction, User, Wallet
from app.services.exceptions import BadRequest, Conflict, IdempotencyKeyConflict, NotFound
from app.services.transfers import create_transfer, create_transfer_idempotent
import app.services.transfers as transfers_service


def _mk_user_and_wallet(db, balance: Decimal) -> Wallet:
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = Wallet(user_id=user.id, balance=balance)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def test_transfer_success(db):
    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    t = create_transfer(db, from_w.id, to_w.id, Decimal("25.50"))

    db.refresh(from_w)
    db.refresh(to_w)

    assert isinstance(t, Transaction)
    assert t.from_wallet_id == from_w.id
    assert t.to_wallet_id == to_w.id
    assert t.amount == Decimal("25.50")
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

    count = db.query(Transaction).count()
    assert count == 0


def test_idempotent_transfer_db_fallback_same_key_returns_same_tx(monkeypatch, db):
    monkeypatch.setattr(transfers_service, "get_redis", lambda: None)

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    tx1 = create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "db-fallback-1")
    tx2 = create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "db-fallback-1")

    db.refresh(from_w)
    db.refresh(to_w)

    assert tx1.id == tx2.id
    assert from_w.balance == Decimal("90.00")
    assert to_w.balance == Decimal("10.00")


def test_idempotent_transfer_db_fallback_conflict(monkeypatch, db):
    monkeypatch.setattr(transfers_service, "get_redis", lambda: None)

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("10.00"), "db-fallback-2")

    with pytest.raises(IdempotencyKeyConflict):
        create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("20.00"), "db-fallback-2")


def test_idempotent_transfer_redis_error_falls_back_to_db(monkeypatch, db):
    class FailingRedis:
        def get(self, key):
            raise RedisError("redis is down")

    monkeypatch.setattr(transfers_service, "get_redis", lambda: FailingRedis())

    from_w = _mk_user_and_wallet(db, Decimal("100.00"))
    to_w = _mk_user_and_wallet(db, Decimal("0.00"))

    tx1 = create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("5.00"), "redis-fail-1")
    tx2 = create_transfer_idempotent(db, from_w.id, to_w.id, Decimal("5.00"), "redis-fail-1")

    assert tx1.id == tx2.id
    assert db.query(Transaction).count() == 1
