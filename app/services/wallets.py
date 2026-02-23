from decimal import Decimal

from sqlalchemy.orm import Session

from app.cache import get_cache
from app.db.models import User, Wallet
from app.db.tx import on_commit

from .exceptions import UserNotFound, WalletNotFound

CACHE_TTL_SECONDS = 60
WALLET_CACHE_PREFIX = "wallet:"


def _get_wallet_from_db(db: Session, wallet_id: int) -> Wallet:
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound(wallet_id)
    return wallet


def get_wallet_cached(db: Session, wallet_id: int) -> dict:
    cache = get_cache()
    key = f"{WALLET_CACHE_PREFIX}{wallet_id}"

    data = cache.get(key)
    if data:
        return data

    wallet = _get_wallet_from_db(db, wallet_id)
    data = {
        "id": wallet.id,
        "balance": str(wallet.balance),
        "user_id": wallet.user_id,
    }

    cache.set(key, data, ex=CACHE_TTL_SECONDS)
    return data


def invalidate_wallet_cache(wallet_id: int) -> None:
    get_cache().delete(f"{WALLET_CACHE_PREFIX}{wallet_id}")


def get_wallet(db: Session, wallet_id: int) -> Wallet:
    return _get_wallet_from_db(db, wallet_id)


def create_wallet_for_user(db: Session, user_id: int) -> Wallet:
    initial_balance = Decimal("100.00")
    user = db.get(User, user_id)
    if not user:
        raise UserNotFound(user_id)

    wallet = Wallet(user_id=user.id, balance=initial_balance)
    db.add(wallet)

    on_commit(db, invalidate_wallet_cache, wallet.id)
    return wallet
