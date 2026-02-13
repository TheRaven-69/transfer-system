from sqlalchemy.orm import Session

from app.db.models import Wallet
from .exceptions import WalletNotFound


def get_wallet(db: Session, wallet_id: int) -> Wallet:
    wallet = db.get(Wallet, wallet_id)
    if not wallet:
        raise WalletNotFound(wallet_id)
    return wallet
