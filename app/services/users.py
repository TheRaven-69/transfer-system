import logging

from sqlalchemy.orm import Session

from app.db.models import User
from app.db.tx import transaction_scope

from .exceptions import UserNotFound, UserWalletNotFound
from .wallets import create_wallet_for_user

logger = logging.getLogger(__name__)


def create_user(db: Session) -> User:
    logger.info("User creation started")
    with transaction_scope(db):
        user = User()
        db.add(user)
        db.flush()
        wallet = create_wallet_for_user(db, user.id)
        user.wallet = wallet
        logger.info(
            "User created successfully: user_id=%s wallet_id=%s", user.id, wallet.id
        )
    return user


def create_user_with_wallet(db: Session) -> User:
    user = create_user(db)
    if user.wallet is None:
        logger.warning("User created without wallet: user_id=%s", user.id)
        raise UserWalletNotFound(user.id)
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    logger.info("Fetching user: user_id=%s", user_id)
    user = db.get(User, user_id)
    if not user:
        logger.warning("User not found: user_id=%s", user_id)
        raise UserNotFound(user_id)
    return user


def get_user_by_id_with_wallet(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)
    if user.wallet is None:
        logger.warning("Wallet for user not found: user_id=%s", user_id)
        raise UserWalletNotFound(user_id)
    logger.info(
        "User with wallet fetched successfully: user_id=%s wallet_id=%s",
        user_id,
        user.wallet.id,
    )
    return user
