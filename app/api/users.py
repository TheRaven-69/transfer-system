from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.users import (
    create_user_with_wallet as create_user,
)
from app.services.users import (
    get_user_by_id_with_wallet as get_user_by_id,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def post_user(db: Session = Depends(get_db)):
    created_user = create_user(db)
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
    return {
        "id": user_inform.id,
        "created_at": user_inform.created_at,
        "wallet": {
            "id": user_inform.wallet.id,
            "balance": user_inform.wallet.balance,
        },
    }
