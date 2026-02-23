import hashlib
from contextlib import nullcontext
from decimal import Decimal

from redis import RedisError
from sqlalchemy import select
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


def _idempotency_redis_key(idempotency_key: str) -> str:
    return f"idem:transfer:{idempotency_key}"


def create_transfer_idempotent(
    db: Session,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Transaction:
    redis_client = get_redis()
    if redis_client is None:
        raise RequestInProgress()

    request_hash = _hash_transfer_request(from_wallet_id, to_wallet_id, amount)
    key = _idempotency_redis_key(idempotency_key)

    try:
        key_created = redis_client.set(
            key,
            request_hash,
            ex=IDEM_RESULT_TTL_SEC,
            nx=True, # Only set if not exists
        )
        if not key_created:
            existing_hash = redis_client.get(key)
            if existing_hash and existing_hash.decode("utf-8") != request_hash:
                raise IdempotencyKeyConflict()
            raise RequestInProgress()

        try:
            tx = create_transfer(db, from_wallet_id, to_wallet_id, amount)
        except Exception:
            redis_client.delete(key)
            raise

    except RedisError:
        raise RequestInProgress()

    send_transaction_notification.delay(tx.id)
    return tx
