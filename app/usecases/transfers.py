import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Transaction, Wallet
from app.idempotency import (
    get_idempotency_manager,
    hash_payload,
    idempotency_key_fingerprint,
)
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
) -> Transaction:
    idem = get_idempotency_manager()
    fingerprint = idempotency_key_fingerprint(idempotency_key)

    payload = {
        "from_wallet_id": from_wallet_id,
        "to_wallet_id": to_wallet_id,
        "amount": str(amount),
    }
    request_hash = hash_payload(payload)

    with idem.reserve(f"transfer:{idempotency_key}", request_hash):
        transfer = create_transfer(db, from_wallet_id, to_wallet_id, amount)

    _post_transfer_side_effects(db, transfer, fingerprint)
    return transfer
