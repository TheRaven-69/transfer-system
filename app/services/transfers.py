import hashlib
import json
import time
from contextlib import nullcontext
from decimal import Decimal

from redis import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache import get_redis
from app.db.models import Transaction, Wallet
from app.services.wallets import invalidate_wallet_cache
from app.tasks.notifications import send_transaction_notification

from .exceptions import (
    CannotTransferToSameWallet,
    IdempotencyKeyConflict,
    InsufficientFunds,
    InvalidTransferAmount,
    RequestInProgress,
    TransferAmountRequired,
    WalletNotFound,
)

IDEM_RESULT_TTL_SEC = 24 * 3600
IDEM_LOCK_TTL_SEC = 30
IDEM_WAIT_RETRIES = 5
IDEM_WAIT_SLEEP_SEC = 0.2


def create_transfer(db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise CannotTransferToSameWallet()
    if amount is None:
        raise TransferAmountRequired()
    if amount <= 0:
        raise InvalidTransferAmount()

    first_id, second_id = sorted([from_wallet_id, to_wallet_id])

    tx_context = nullcontext() if db.in_transaction() else db.begin()
    with tx_context:
        wallets = (
            db.execute(
                select(Wallet)
                .where(Wallet.id.in_([first_id, second_id]))
                .with_for_update()
            )
            .scalars()
            .all()
        )

        wallet_map = {w.id: w for w in wallets}
        from_wallet = wallet_map.get(from_wallet_id)
        to_wallet = wallet_map.get(to_wallet_id)

        if not from_wallet:
            raise WalletNotFound(from_wallet_id)
        if not to_wallet:
            raise WalletNotFound(to_wallet_id)

        if from_wallet.balance < amount:
            raise InsufficientFunds()

        from_wallet.balance -= amount
        to_wallet.balance += amount

        transfer = Transaction(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=amount,
        )
        db.add(transfer)
        db.flush()
        db.refresh(transfer)

    invalidate_wallet_cache(from_wallet_id)
    invalidate_wallet_cache(to_wallet_id)

    return transfer


def _hash_transfer_request(from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> str:
    payload = f"{from_wallet_id}:{to_wallet_id}:{str(amount)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_transfer_idempotent(
    db: Session,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Transaction:
    redis = get_redis()
    if redis is None:
        return _create_transfer_idempotent_db(db, from_wallet_id, to_wallet_id, amount, idempotency_key)

    req_hash = _hash_transfer_request(from_wallet_id, to_wallet_id, amount)

    result_key = f"idem:transfer:{idempotency_key}:result"
    lock_key = f"idem:transfer:{idempotency_key}:lock"

    try:
        cached = redis.get(result_key)
    except RedisError:
        return _create_transfer_idempotent_db(db, from_wallet_id, to_wallet_id, amount, idempotency_key)

    if cached:
        data = json.loads(cached)
        if data.get("request_hash") != req_hash:
            raise IdempotencyKeyConflict()

        tx_id = data.get("tx_id")
        tx = db.get(Transaction, tx_id)
        if tx is not None:
            return tx

    existing = db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key)).scalar_one_or_none()

    if existing is not None:
        if existing.request_hash != req_hash:
            raise IdempotencyKeyConflict()

        payload = {"request_hash": req_hash, "tx_id": existing.id}
        try:
            redis.set(result_key, json.dumps(payload), ex=IDEM_RESULT_TTL_SEC)
        except RedisError:
            pass
        return existing

    try:
        locked = redis.set(lock_key, "1", nx=True, ex=IDEM_LOCK_TTL_SEC)
    except RedisError:
        return _create_transfer_idempotent_db(db, from_wallet_id, to_wallet_id, amount, idempotency_key)

    if not locked:
        for _ in range(IDEM_WAIT_RETRIES):
            time.sleep(IDEM_WAIT_SLEEP_SEC)
            try:
                cached = redis.get(result_key)
            except RedisError:
                raise RequestInProgress()
            if cached:
                data = json.loads(cached)
                if data.get("request_hash") != req_hash:
                    raise IdempotencyKeyConflict()

                tx_id = data.get("tx_id")
                tx = db.get(Transaction, tx_id)
                if tx is not None:
                    return tx

        raise RequestInProgress()

    try:
        tx = create_transfer(db, from_wallet_id, to_wallet_id, amount)

        tx.idempotency_key = idempotency_key
        tx.request_hash = req_hash
        db.add(tx)
        db.commit()
        db.refresh(tx)
        send_transaction_notification.delay(tx.id)

        payload = {"request_hash": req_hash, "tx_id": tx.id}
        try:
            redis.set(result_key, json.dumps(payload), ex=IDEM_RESULT_TTL_SEC)
        except RedisError:
            pass

        return tx

    finally:
        try:
            redis.delete(lock_key)
        except RedisError:
            pass


def _create_transfer_idempotent_db(
    db: Session,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Transaction:
    req_hash = _hash_transfer_request(from_wallet_id, to_wallet_id, amount)

    existing = db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key)).scalar_one_or_none()

    if existing is not None:
        if existing.request_hash != req_hash:
            raise IdempotencyKeyConflict()
        return existing

    db.rollback()

    try:
        tx = create_transfer(db, from_wallet_id, to_wallet_id, amount)

        tx.idempotency_key = idempotency_key
        tx.request_hash = req_hash
        db.add(tx)
        db.commit()
        db.refresh(tx)
        send_transaction_notification.delay(tx.id)
        return tx

    except IntegrityError:
        db.rollback()
        existing = db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key)).scalar_one()

        if existing.request_hash != req_hash:
            raise IdempotencyKeyConflict()
        return existing
