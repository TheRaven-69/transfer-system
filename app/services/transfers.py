from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Transaction, Wallet
from app.db.tx import on_commit, transaction_scope
from app.idempotency import get_idempotency_manager, hash_payload
from app.services.wallets import invalidate_wallet_cache
from app.tasks.notifications import send_transaction_notification

from .exceptions import (
    CannotTransferToSameWallet,
    InsufficientFunds,
    InvalidTransferAmount,
    TransferAmountRequired,
    WalletNotFound,
)

IDEM_RESULT_TTL_SEC = 24 * 3600


def create_transfer(
    db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal
) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise CannotTransferToSameWallet()
    if amount is None:
        raise TransferAmountRequired()
    if amount <= 0:
        raise InvalidTransferAmount()

    first_id, second_id = sorted([from_wallet_id, to_wallet_id])

    with transaction_scope(db):
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

        on_commit(db, invalidate_wallet_cache, from_wallet_id)
        on_commit(db, invalidate_wallet_cache, to_wallet_id)
        on_commit(db, send_transaction_notification.delay, transfer.id)

    return transfer


def create_transfer_idempotent(
    db: Session,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str,
) -> Transaction:
    idem = get_idempotency_manager()

    payload = {
        "from_wallet_id": from_wallet_id,
        "to_wallet_id": to_wallet_id,
        "amount": str(amount),
    }
    request_hash = hash_payload(payload)

    # Use context manager for reservation and automatic cleanup on failure
    with idem.reserve(f"transfer:{idempotency_key}", request_hash):
        return create_transfer(db, from_wallet_id, to_wallet_id, amount)
