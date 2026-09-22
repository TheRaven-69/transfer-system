from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.services.exceptions import AccessDenied
from app.usecases.wallets import get_wallet_cached

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{wallet_id}")
def get_wallet_(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    wallet = get_wallet_cached(db, wallet_id)
    if wallet["user_id"] != current_user.id:
        raise AccessDenied()

    return {
        "id": wallet["id"],
        "balance": wallet["balance"],
        "user_id": wallet["user_id"],
    }
