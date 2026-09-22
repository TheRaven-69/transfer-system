from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.services.exceptions import AccessDenied
from app.services.users import (
    get_user_by_id_with_wallet as get_user_by_id,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise AccessDenied()
    user_inform = get_user_by_id(db, user_id)
    return {
        "id": user_inform.id,
        "username": user_inform.username,
        "email": user_inform.email,
        "created_at": user_inform.created_at,
        "wallet": {
            "id": user_inform.wallet.id,
            "balance": user_inform.wallet.balance,
        },
    }
