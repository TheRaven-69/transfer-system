import json
from decimal import Decimal
from sqlalchemy.orm import Session
from redis import RedisError

from app.cache import get_redis
from app.db.models import Wallet, User
from .exceptions import WalletNotFound, UserNotFound, CacheUnavailable

CACHE_TTL_SECONDS = 60  # стартово, потім можна 300
WALLET_CACHE_PREFIX = "wallet:"


def _get_wallet_from_db(db: Session, wallet_id: int) -> Wallet:
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound(wallet_id)
    return wallet


def get_wallet_cached(db: Session, wallet_id: int) -> dict:
    r = None
    key = f"wallet:{wallet_id}"
    try:
        r = get_redis()
    except CacheUnavailable:
        r = None

    if r:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except RedisError:
            pass        

    wallet = _get_wallet_from_db(db, wallet_id)

    data = {
        "id": wallet.id,
        "balance": str(wallet.balance),
        "user_id": wallet.user_id,
    }

    if r:
        try:
            r.set(key, json.dumps(data), ex=CACHE_TTL_SECONDS)
        except RedisError:
            pass  

    return data


def invalidate_wallet_cache(wallet_id: int) -> None:
    r = get_redis()
    if r:
        try:
            r.delete(f"wallet:{wallet_id}")
        except RedisError:
            pass    


def get_wallet(db: Session, wallet_id: int) -> Wallet:
    return _get_wallet_from_db(db, wallet_id)


def create_wallet_for_user(db: Session, user_id: int) -> Wallet:
    initial_balance = Decimal("100.00")
    user = db.get(User, user_id)
    if not user:
        raise UserNotFound(user_id)

    wallet = Wallet(user_id=user.id, balance=initial_balance)
    db.add(wallet)
    db.flush()
    db.refresh(wallet)

    invalidate_wallet_cache(wallet.id)

    return wallet
