import logging

from sqlalchemy.orm import Session

from app.db.models import User
from app.db.tx import on_commit, transaction_scope

from .exceptions import UserNotFound, UserWalletNotFound
from .wallets import create_wallet_for_user

logger = logging.getLogger(__name__)


def _log_user_created(user_id: int, wallet_id: int, balance: str) -> None:
    logger.info(
        "user_created",
        extra={
            "extra_fields": {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "balance": balance,
            }
        },
    )


def create_user(db: Session) -> User:
    with transaction_scope(db):
        user = User()
        db.add(user)
        db.flush()
        wallet = create_wallet_for_user(db, user.id)
        user.wallet = wallet
        on_commit(
            db,
            _log_user_created,
            user.id,
            wallet.id,
            str(wallet.balance),
        )
    return user


def create_user_with_wallet(db: Session) -> User:
    user = create_user(db)
    if user.wallet is None:
        raise UserWalletNotFound(user.id)
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise UserNotFound(user_id)
    return user


def get_user_by_id_with_wallet(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)
    if user.wallet is None:
        raise UserWalletNotFound(user_id)
    return user
