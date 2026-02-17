from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.transfers import create_transfer_idempotent as create_transfer

from decimal import Decimal

router = APIRouter(prefix="/transfers", tags=["transfers"])

@router.post("")
def transfer(from_wallet_id: int, 
             to_wallet_id: int, 
             amount: Decimal,
             idempotency_key: str = Header(..., alias="Idempotency-Key"), 
             db: Session = Depends(get_db)):
    transfer_between_wallets = create_transfer(db, from_wallet_id, to_wallet_id, amount, idempotency_key)
    return {
        "id": transfer_between_wallets.id,
        "from_wallet_id": transfer_between_wallets.from_wallet_id,
        "to_wallet_id": transfer_between_wallets.to_wallet_id,
        "amount": transfer_between_wallets.amount,
        "created_at": transfer_between_wallets.created_at,                
        }
