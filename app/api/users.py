from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.users import create_user, get_user_by_id
from app.services.exceptions import UserWalletNotFound


from app.db.session import get_db


router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def post_user(db: Session = Depends(get_db)):
    created_user = create_user(db)
    if created_user.wallet is None:
        raise UserWalletNotFound(created_user.id)
    return {
        "id": created_user.id,
        "created_at": created_user.created_at,
        "wallet": {
            "balance": created_user.wallet.balance,
        },
    }


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user_inform = get_user_by_id(db, user_id)
    if user_inform.wallet is None:
        raise UserWalletNotFound(user_id)
    return {
        "id": user_inform.id,
        "created_at": user_inform.created_at,
        "wallet": {
            "id": user_inform.wallet.id,
            "balance": user_inform.wallet.balance,
        },
    }
