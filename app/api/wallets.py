from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Wallet

from decimal import Decimal

router = APIRouter(prefix="/wallet", tags=["wallets"])


@router.get("/{wallet_id}")
def get_wallet(wallet_id: int, db: Session = Depends(get_db)):
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return{
        "id": wallet.id,
        "balance": wallet.balance,
        "user_id": wallet.user_id,
    }


@router.post("")
def create_wallet(user_id: int, initial_balance: Decimal = Decimal("0"), db: Session = Depends(get_db)):
    if initial_balance < 0:
        raise HTTPException(status_code=400, detail="Initial balance cannot be negative")
    
    wallet = Wallet(
        user_id=user_id,
        balance = initial_balance,
    )

    db.add(wallet)
    db.commit()
    db.refresh(wallet)