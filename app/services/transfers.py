from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Transaction, Wallet
from .exceptions import (
    CannotTransferToSameWallet,
    DestinationWalletNotFound,
    InsufficientFunds,
    InvalidTransferAmount,
    SourceWalletNotFound,
    TransferAmountRequired,
)


def create_transfer(db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise CannotTransferToSameWallet()

    if amount is None:
        raise TransferAmountRequired()

    if amount <= 0:
        raise InvalidTransferAmount()

    from_wallet = db.get(Wallet, from_wallet_id)
    if not from_wallet:
        raise SourceWalletNotFound(from_wallet_id)

    to_wallet = db.get(Wallet, to_wallet_id)
    if not to_wallet:
        raise DestinationWalletNotFound(to_wallet_id)

    if from_wallet.balance < amount:
        raise InsufficientFunds()

    with db.begin_nested():
        from_wallet.balance -= amount
        to_wallet.balance += amount

        transfer = Transaction(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=amount,
        )

        db.add(transfer)
        db.commit()

    db.refresh(transfer)
    return transfer
