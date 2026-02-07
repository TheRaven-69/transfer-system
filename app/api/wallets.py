from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.wallets import get_wallet_by_id, create_wallet_with_autouser

from app.db.session import get_db


router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("")
def auto_create(db: Session = Depends(get_db)):
    wallet = create_wallet_with_autouser(db)
    return {
        "wallet": {"id": wallet.id,
            "balance": wallet.balance,
            "user_id": wallet.user_id,
            },
        "user": {
            "id": wallet.user.id,
            "created_at": wallet.user.created_at
        },   
    }
    

@router.get("/{wallet_id}")
def get_wallet(wallet_id: int, db: Session = Depends(get_db)):
    wallet = get_wallet_by_id(db, wallet_id)
    
    return{
        "id": wallet.id,
        "balance": wallet.balance,
        "user_id": wallet.user_id,
    }

