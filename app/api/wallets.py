from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.metrics import WALLET_CACHE_HITS_TOTAL, WALLET_CACHE_MISSES_TOTAL
from app.db.session import get_db
from app.services.wallets import get_wallet_cached

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{wallet_id}")
def get_wallet_(wallet_id: int, db: Session = Depends(get_db)):
    result = get_wallet_cached(db, wallet_id)
    if result.cache_hit:
        WALLET_CACHE_HITS_TOTAL.inc()
    else:
        WALLET_CACHE_MISSES_TOTAL.inc()

    wallet = result.data

    return {
        "id": wallet["id"],
        "balance": wallet["balance"],
        "user_id": wallet["user_id"],
    }
