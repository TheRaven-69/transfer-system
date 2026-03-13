import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.wallets import get_wallet_cached

router = APIRouter(prefix="/wallets", tags=["wallets"])

logger = logging.getLogger(__name__)


@router.get("/{wallet_id}")
def get_wallet_(wallet_id: int, db: Session = Depends(get_db)):
    logger.info("Get wallet endpoint called: wallet_id=%s", wallet_id)
    wallet = get_wallet_cached(db, wallet_id)
    logger.info("Wallet returned successfully: wallet_id=%s", wallet_id)

    return {
        "id": wallet["id"],
        "balance": wallet["balance"],
        "user_id": wallet["user_id"],
    }
