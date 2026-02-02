from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from sqlalchemy import Numeric, Integer, DateTime, ForeignKey, CheckConstraint, func
from datetime import datetime
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    wallet: Mapped["Wallet"] = relationship(uselist=False, back_populates="user")

class Wallet(Base):
    __tablename__ = "wallets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0", nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    user: Mapped["User"] = relationship(back_populates="wallet")
    
    outgoing_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="from_wallet",
        foreign_keys="[Transaction.from_wallet_id]",
    )
    incoming_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="to_wallet",
        foreign_keys="[Transaction.to_wallet_id]",
    )

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("from_wallet_id <> to_wallet_id", name="ck_tx_wallets_not_same"),)
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    from_wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wallets.id"), nullable=False)
    to_wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wallets.id"), nullable=False)
    
    from_wallet: Mapped["Wallet"] = relationship(
        foreign_keys=[from_wallet_id], 
        back_populates="outgoing_transactions"
    )
    to_wallet: Mapped["Wallet"] = relationship(
        foreign_keys=[to_wallet_id], 
        back_populates="incoming_transactions"
    )