from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(uselist=False, back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), server_default="0", nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )

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
    __table_args__ = (
        CheckConstraint(
            "from_wallet_id <> to_wallet_id", name="ck_tx_wallets_not_same"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    from_wallet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wallets.id"), nullable=False
    )
    to_wallet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wallets.id"), nullable=False
    )

    from_wallet: Mapped["Wallet"] = relationship(
        foreign_keys=[from_wallet_id], back_populates="outgoing_transactions"
    )
    to_wallet: Mapped["Wallet"] = relationship(
        foreign_keys=[to_wallet_id], back_populates="incoming_transactions"
    )
