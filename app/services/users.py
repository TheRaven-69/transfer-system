from sqlalchemy.orm import Session

from app.db.models import User

from .exceptions import UserNotFound, UserWalletNotFound


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
