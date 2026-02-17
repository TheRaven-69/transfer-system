from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Wallet, Transaction
from app.services.wallets import invalidate_wallet_cache
from .exceptions import (
    CannotTransferToSameWallet,
    TransferAmountRequired,
    InvalidTransferAmount,
    WalletNotFound,
    InsufficientFunds,
)

def create_transfer(db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise CannotTransferToSameWallet()
    if amount is None:
        raise TransferAmountRequired()
    if amount <= 0:
        raise InvalidTransferAmount()


    first_id, second_id = sorted([from_wallet_id, to_wallet_id])

    
    with db.begin_nested(): 
        wallets = (
            db.execute(
                select(Wallet)
                .where(Wallet.id.in_([first_id, second_id]))
                .with_for_update()
            )
            .scalars()
            .all()
        )

        wallet_map = {w.id: w for w in wallets}
        from_wallet = wallet_map.get(from_wallet_id)
        to_wallet = wallet_map.get(to_wallet_id)

        if not from_wallet:
            raise WalletNotFound(from_wallet_id)
        if not to_wallet:
            raise WalletNotFound(to_wallet_id)

        if from_wallet.balance < amount:
            raise InsufficientFunds()

        from_wallet.balance -= amount
        to_wallet.balance += amount

        transfer = Transaction(
            from_wallet_id=from_wallet.id,
            to_wallet_id=to_wallet.id,
            amount=amount,
        )
        db.add(transfer)
        db.flush()      
        db.refresh(transfer)

    invalidate_wallet_cache(from_wallet_id)
    invalidate_wallet_cache(to_wallet_id)

    return transfer

