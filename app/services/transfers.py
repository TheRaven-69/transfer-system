from sqlalchemy.orm import Session
from app.db.models import Wallet, Transaction
from decimal import Decimal
from .exceptions import BadRequest, NotFound, Conflict


def create_transfer(db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise BadRequest("Cannot transfer to the same wallet")

    if amount is None:
        raise BadRequest("Amount is required")

    if amount <= 0:
        raise BadRequest("Amount must be greater than zero")
    
    with db.begin_nested():
        from_wallet = db.get(Wallet, from_wallet_id)
        if not from_wallet:
            raise NotFound(f"From wallet with id {from_wallet_id} not found")
        
        to_wallet = db.get(Wallet, to_wallet_id)
        if not to_wallet:
            raise NotFound(f"To wallet with id {to_wallet_id} not found")
        
        if from_wallet.balance < amount:
            raise Conflict("Insufficient funds")
        
        from_wallet.balance -= amount
        to_wallet.balance += amount

        transfer = Transaction(
            from_wallet_id = from_wallet.id,
            to_wallet_id = to_wallet.id,
            amount = amount,
        )

        db.add(transfer)

    db.refresh(transfer)
    return transfer     