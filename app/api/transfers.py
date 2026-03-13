import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.transfers import create_transfer_idempotent as create_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])

logger = logging.getLogger(__name__)


@router.post("")
def transfer(
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    logger.info(
        "Transfer endpoint called: from_wallet_id=%s to_wallet_id=%s amount=%s",
        from_wallet_id,
        to_wallet_id,
        amount,
    )
    transfer = create_transfer(
        db, from_wallet_id, to_wallet_id, amount, idempotency_key
    )
    return {
        "id": transfer.id,
        "from_wallet_id": transfer.from_wallet_id,
        "to_wallet_id": transfer.to_wallet_id,
        "amount": transfer.amount,
        "created_at": transfer.created_at,
    }
