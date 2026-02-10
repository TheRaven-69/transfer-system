from sqlalchemy.orm import Session
from decimal import Decimal

from .exceptions import NotFound
from app.db.models import User, Wallet


def create_user(db: Session) -> User:
    user = User()
    db.add(user)
    db.flush()
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFound(f"User with id {user_id} not found.")
    return user


def create_wallet_for_user(db: Session, user_id: int) -> Wallet:
    initial_balance = Decimal("100.00")
    user = db.get(User, user_id)
    if not user:
        raise NotFound(f"User with id {user_id} not found.")
    
    with db.begin_nested():
        wallet  = Wallet(user_id = user.id, balance = initial_balance)
        db.add(wallet)
        db.flush()
    
    db.refresh(wallet)
    return wallet
