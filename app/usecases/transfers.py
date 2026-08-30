import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Transaction, Wallet
from app.db.tx import transaction_scope
from app.idempotency import (
    get_idempotency_manager,
    hash_payload,
    idempotency_key_fingerprint,
)
from app.services.exceptions import AccessDenied, WalletNotFound
from app.services.transfers import create_transfer
from app.tasks.transfer_notifications import enqueue_transfer_notification
from app.usecases.wallets import invalidate_wallet_cache

logger = logging.getLogger(__name__)


def _post_transfer_side_effects(
    db: Session,
    transfer: Transaction,
    idempotency_fingerprint: str,
) -> None:
    invalidate_wallet_cache(transfer.from_wallet_id)
    invalidate_wallet_cache(transfer.to_wallet_id)

    from_wallet = db.get(Wallet, transfer.from_wallet_id)
    user_id = from_wallet.user_id if from_wallet else None

    try:
        enqueue_transfer_notification(
            transfer.id,
            user_id,
            idempotency_fingerprint,
        )
    except Exception:
        logger.exception(
            "Failed to enqueue transfer notification: transfer_id=%s",
            transfer.id,
        )


def create_transfer_idempotent(
    db: Session,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str,
    actor_user_id: int | None = None,
) -> Transaction:
    if actor_user_id is not None:
        with transaction_scope(db):
            source_wallet = db.get(Wallet, from_wallet_id)
            if source_wallet is None:
                raise WalletNotFound(from_wallet_id)
            if source_wallet.user_id != actor_user_id:
                raise AccessDenied()

    idem = get_idempotency_manager()
    fingerprint = idempotency_key_fingerprint(idempotency_key)

    payload = {
        "from_wallet_id": from_wallet_id,
        "to_wallet_id": to_wallet_id,
        "amount": str(amount),
    }
    request_hash = hash_payload(payload)
    idempotency_scope = (
        f"user:{actor_user_id}" if actor_user_id is not None else "internal"
    )

    with idem.reserve(f"transfer:{idempotency_scope}:{idempotency_key}", request_hash):
        transfer = create_transfer(
            db,
            from_wallet_id,
            to_wallet_id,
            amount,
            actor_user_id=actor_user_id,
        )

    _post_transfer_side_effects(db, transfer, fingerprint)
    return transfer
