import hashlib

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Wallet, Transaction
from app.services.wallets import invalidate_wallet_cache
from .exceptions import (
    CannotTransferToSameWallet,
    TransferAmountRequired,
    InvalidTransferAmount,
    WalletNotFound,
    InsufficientFunds,
    IdempotencyKeyConflict
)


def create_transfer(db: Session, from_wallet_id: int, to_wallet_id: int, amount: Decimal) -> Transaction:
    if from_wallet_id == to_wallet_id:
        raise CannotTransferToSameWallet()
    if amount is None:
        raise TransferAmountRequired()
    if amount <= 0:
        raise InvalidTransferAmount()


    first_id, second_id = sorted([from_wallet_id, to_wallet_id])

    
    with db.begin():
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

def _hash_transfer_request(from_wallet_id: int,
                           to_wallet_id: int,
                           amount: Decimal) -> str:
    payload = f"{from_wallet_id}:{to_wallet_id}:{str(amount)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_transfer_idempotent(db: Session, 
                               from_wallet_id: int,
                               to_wallet_id: int,
                               amount: Decimal,
                               idempotency_key: str) -> Transaction:
    request_hash = _hash_transfer_request(from_wallet_id, to_wallet_id, amount)

    existing = db.execute(
    select(Transaction).where(Transaction.idempotency_key == idempotency_key)).scalar_one_or_none()

    if existing is not None:
        if existing.request_hash != request_hash:
            raise IdempotencyKeyConflict()
        return existing
    
    db.rollback()

    try:
        tx = create_transfer(db, from_wallet_id, to_wallet_id, amount)

        tx.idempotency_key = idempotency_key
        tx.request_hash = request_hash

        db.add(tx)
        db.commit()
        db.refresh(tx)

        return tx
    
    except IntegrityError:
        db.rollback()

        existing = db.execute(
            select(Transaction).where(Transaction.idempotency_key == idempotency_key)).scalar_one()
        
        if existing.request_hash != request_hash:
            raise IdempotencyKeyConflict()
        
        return existing