from decimal import Decimal

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.metrics import TRANSFER_AMOUNT_TOTAL, TRANSFERS_CREATED_TOTAL
from app.db.session import get_db
from app.services.transfers import create_transfer_idempotent as create_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("")
def transfer(
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    transfer = create_transfer(
        db, from_wallet_id, to_wallet_id, amount, idempotency_key
    )
    TRANSFERS_CREATED_TOTAL.inc()
    TRANSFER_AMOUNT_TOTAL.inc(float(transfer.amount))
    return {
        "id": transfer.id,
        "from_wallet_id": transfer.from_wallet_id,
        "to_wallet_id": transfer.to_wallet_id,
        "amount": transfer.amount,
        "created_at": transfer.created_at,
    }
