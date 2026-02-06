from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.users import create_user, get_user_by_id
from app.services.wallets import create_wallet_for_user

from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("")
def post_user(db: Session = Depends(get_db)):
    created_user = create_user(db)
    return {
        "id": created_user.id,
        "created_at": created_user.created_at
    }

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user_inform = get_user_by_id(db, user_id) 
    return {
        "id": user_inform.id,
        "created_at": user_inform.created_at
    }  

@router.post("/{user_id}/wallet")
def create_wallet(user_id: int, db: Session = Depends(get_db)):
    wallet = create_wallet_for_user(db, user_id)
    return {
        "id": wallet.id,
        "balance": wallet.balance,
        "user_id": wallet.user_id,

    }
