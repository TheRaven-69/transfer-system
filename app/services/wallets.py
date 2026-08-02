import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import User, Wallet
from app.db.tx import on_commit

from .exceptions import UserNotFound, WalletNotFound

logger = logging.getLogger(__name__)


def _log_wallet_created(wallet_id: int, user_id: int, balance: str) -> None:
    logger.info(
        "wallet_created",
        extra={
            "extra_fields": {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "balance": balance,
            }
        },
    )


def _get_wallet_from_db(db: Session, wallet_id: int) -> Wallet:
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound(wallet_id)
    return wallet


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

    on_commit(
        db,
        _log_wallet_created,
        wallet.id,
        user_id,
        str(wallet.balance),
    )
    return wallet
