from sqlalchemy.orm import Session

from app.db.models import User, Wallet
from .exceptions import UserNotFound, UserWalletNotFound
from .wallets import create_wallet_for_user


def create_user(db: Session) -> User:
    with db.begin():
        user = User()
        db.add(user)
        db.flush()
        wallet = create_wallet_for_user(db, user.id)
        user.wallet = wallet
    db.refresh(user)
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
