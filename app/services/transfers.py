import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.metrics import TRANSFER_OPERATIONS_TOTAL
from app.db.models import Transaction, Wallet
from app.db.tx import on_commit, transaction_scope
from app.idempotency import get_idempotency_manager, hash_payload
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

logger = logging.getLogger(__name__)


def _track_transfer_operation(status: str) -> None:
    TRANSFER_OPERATIONS_TOTAL.labels(status=status).inc()


def create_transfer(
    db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal
) -> Transaction:
    try:
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
            db.flush()

            on_commit(db, invalidate_wallet_cache, from_wallet_id)
            on_commit(db, invalidate_wallet_cache, to_wallet_id)
            on_commit(db, send_transaction_notification.delay, transfer.id)

        _track_transfer_operation("success")
        logger.info(
            "Transfer completed successfully: transfer_id=%s from_wallet_id=%s to_wallet_id=%s amount=%s",
            transfer.id,
            from_wallet_id,
            to_wallet_id,
            amount,
        )
        return transfer
    except CannotTransferToSameWallet:
        _track_transfer_operation("same_wallet")
        raise
    except TransferAmountRequired:
        _track_transfer_operation("amount_required")
        raise
    except InvalidTransferAmount:
        _track_transfer_operation("invalid_amount")
        raise
    except WalletNotFound:
        _track_transfer_operation("wallet_not_found")
        raise
    except InsufficientFunds:
        _track_transfer_operation("insufficient_funds")
        raise
    except Exception:
        _track_transfer_operation("internal_error")
        raise


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

    try:
        with idem.reserve(f"transfer:{idempotency_key}", request_hash):
            return create_transfer(db, from_wallet_id, to_wallet_id, amount)
    except IdempotencyKeyConflict:
        _track_transfer_operation("idempotency_conflict")
        raise
    except RequestInProgress:
        _track_transfer_operation("request_in_progress")
        raise
