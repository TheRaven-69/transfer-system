from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import User, Wallet
from .exceptions import UserNotFound


def create_user(db: Session) -> User:
    with db.begin_nested():
        user = User()
        db.add(user)
        db.flush()
        wallet = _create_wallet_for_user(db, user.id)
        user.wallet = wallet
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise UserNotFound(user_id)
    return user


def _create_wallet_for_user(db: Session, user_id: int) -> Wallet:
    initial_balance = Decimal("100.00")
    user = db.get(User, user_id)
    if not user:
        raise UserNotFound(user_id)

    wallet = Wallet(user_id=user.id, balance=initial_balance)
    db.add(wallet)
    db.flush()
    db.refresh(wallet)
    return wallet
