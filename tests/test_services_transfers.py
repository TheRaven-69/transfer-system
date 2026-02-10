from decimal import Decimal
import pytest

from app.db.models import User, Wallet, Transaction
from app.services.transfers import create_transfer
from app.services.exceptions import BadRequest, NotFound, Conflict

def _mk_user_and_wallet(db, balance: Decimal) -> Wallet:
    u = User()
    db.add(u)
    db.flush()
    db.refresh(u)

    w = Wallet(user_id=u.id, balance=balance)
    db.add(w)
    db.flush()
    db.refresh(w)
    return w

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

    # до виклику запам’ятаємо баланс
    before_from = from_w.balance
    before_to = to_w.balance

    with pytest.raises(Conflict):
        create_transfer(db, from_w.id, to_w.id, Decimal("10.00"))

    # оновимо з БД і перевіримо, що нічого не змінилось (атомарність)
    db.refresh(from_w)
    db.refresh(to_w)

    assert from_w.balance == before_from
    assert to_w.balance == before_to

    # і що транзакція не створилась
    count = db.query(Transaction).count()
    assert count == 0
