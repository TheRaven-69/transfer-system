from typing import Any

from sqlalchemy.orm import Session

from app.cache import get_cache
from app.services.wallets import get_wallet

CACHE_TTL_SECONDS = 60
WALLET_CACHE_PREFIX = "wallet:"


def get_wallet_cached(db: Session, wallet_id: int) -> dict[str, Any]:
    cache = get_cache()
    key = f"{WALLET_CACHE_PREFIX}{wallet_id}"

    data = cache.get_wallet(key)
    if data:
        return data

    wallet = get_wallet(db, wallet_id)
    data = {
        "id": wallet.id,
        "balance": str(wallet.balance),
        "user_id": wallet.user_id,
    }

    cache.set(key, data, ex=CACHE_TTL_SECONDS)
    return data


def invalidate_wallet_cache(wallet_id: int) -> None:
    get_cache().delete(f"{WALLET_CACHE_PREFIX}{wallet_id}")
