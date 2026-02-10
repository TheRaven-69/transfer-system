from app.db.models import Wallet, User
from sqlalchemy.orm import Session
from decimal import Decimal

from .exceptions import NotFound


def create_wallet_with_autouser(db: Session) -> Wallet:
    initial_balance = Decimal("100.00")
    with db.begin_nested():
        user = User()
        db.add(user) 
        db.flush()  # Ensure user.id is generated
        wallet = Wallet(user_id = user.id, balance = initial_balance)
        db.add(wallet)
        db.flush()
    db.refresh(wallet)
    _ = wallet.user
    return wallet
    


def get_wallet(db: Session, wallet_id: int) -> Wallet:
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise NotFound(f"Wallet with id {wallet_id} not found.")
    return wallet
