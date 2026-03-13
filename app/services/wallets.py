import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.cache import get_cache
from app.db.models import User, Wallet
from app.db.tx import on_commit

from .exceptions import UserNotFound, WalletNotFound

CACHE_TTL_SECONDS = 60
WALLET_CACHE_PREFIX = "wallet:"

logger = logging.getLogger(__name__)


def _get_wallet_from_db(db: Session, wallet_id: int) -> Wallet:
    logger.info("Fetching wallet from database: wallet_id=%s", wallet_id)
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        logger.warning("Wallet not found: wallet_id=%s", wallet_id)
        raise WalletNotFound(wallet_id)
    return wallet


def get_wallet_cached(db: Session, wallet_id: int) -> dict:
    logger.info("Fetching wallet with cache: wallet_id=%s", wallet_id)
    cache = get_cache()
    key = f"{WALLET_CACHE_PREFIX}{wallet_id}"

    data = cache.get(key)
    if data:
        logger.info("Wallet cache hit: wallet_id=%s", wallet_id)
        return data

    wallet = _get_wallet_from_db(db, wallet_id)
    data = {
        "id": wallet.id,
        "balance": str(wallet.balance),
        "user_id": wallet.user_id,
    }

    cache.set(key, data, ex=CACHE_TTL_SECONDS)
    logger.info("Wallet cached successfully: wallet_id=%s", wallet_id)
    return data


def invalidate_wallet_cache(wallet_id: int) -> None:
    logger.info("Invalidating wallet cache: wallet_id=%s", wallet_id)
    get_cache().delete(f"{WALLET_CACHE_PREFIX}{wallet_id}")


def get_wallet(db: Session, wallet_id: int) -> Wallet:
    return _get_wallet_from_db(db, wallet_id)


def create_wallet_for_user(db: Session, user_id: int) -> Wallet:
    logger.info("Wallet creation started: user_id=%s", user_id)
    initial_balance = Decimal("100.00")
    user = db.get(User, user_id)
    if not user:
        logger.warning("Wallet creation failed: user not found user_id=%s", user_id)
        raise UserNotFound(user_id)

    wallet = Wallet(user_id=user.id, balance=initial_balance)
    db.add(wallet)
    db.flush()

    on_commit(db, invalidate_wallet_cache, wallet.id)
    logger.info(
        "Wallet created successfully: wallet_id=%s user_id=%s balance=%s",
        wallet.id,
        user_id,
        wallet.balance,
    )
    return wallet
