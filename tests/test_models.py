import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Wallet, Transaction
from decimal import Decimal

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()    


def test_create_user_and_wallet(db_session):
    user = User()
    wallet = Wallet(user=user)

    db_session.add(user)
    db_session.add(wallet)
    db_session.commit()

    assert user.id is not None
    assert wallet.id is not None
    assert user.wallet == wallet
    assert wallet.user == user

    db_session.close()


def test_create_transaction_between_wallets(db_session):
    """Test creating transaction between wallets"""
    user1 = User()
    user2 = User()
    wallet1 = Wallet(user=user1, balance=Decimal("100.00"))
    wallet2 = Wallet(user=user2, balance=Decimal("50.00"))
    
    db_session.add_all([user1, user2, wallet1, wallet2])
    db_session.commit()

    transaction = Transaction(
        from_wallet=wallet1,
        to_wallet=wallet2,
        amount=Decimal("22.50")
    )
    db_session.add(transaction)
    db_session.commit()

    assert transaction.id is not None
    assert transaction.amount == Decimal("22.50")
    assert transaction.from_wallet_id == wallet1.id
    assert transaction.to_wallet_id == wallet2.id
    assert transaction in wallet1.outgoing_transactions
    assert transaction in wallet2.incoming_transactions


    db_session.close()


def test_wallet_incoming_transactions_relationship(db_session):
    """Test relationship incoming transactions"""
    user1 = User()
    user2 = User()
    user3 = User()
    wallet1 = Wallet(user=user1, balance=Decimal("100.00"))
    wallet2 = Wallet(user=user2, balance=Decimal("50.00"))
    wallet3 = Wallet(user=user3, balance=Decimal("25.00"))

    db_session.add_all([user1, user2, user3, wallet1, wallet2, wallet3])
    db_session.commit()

    tx1 = Transaction(from_wallet=wallet2, to_wallet=wallet1, amount=Decimal("10.00"))
    tx2 = Transaction(from_wallet=wallet3, to_wallet=wallet1, amount=Decimal("15.00"))
    
    db_session.add_all([tx1, tx2])
    db_session.commit()

    db_session.refresh(wallet1)
    assert len(wallet1.incoming_transactions) == 2
    assert tx1 in wallet1.incoming_transactions
    assert tx2 in wallet1.incoming_transactions

    db_session.refresh(wallet2)
    db_session.refresh(wallet3)
    assert len(wallet2.incoming_transactions) == 0
    assert len(wallet3.incoming_transactions) == 0

    db_session.close()


def test_wallet_outging_transactions_relationship(db_session):
    """Test relationship outging transactions"""
    user1 = User()
    user2 = User()
    user3 = User()
    wallet1 = Wallet(user=user1, balance=Decimal("100.00"))
    wallet2 = Wallet(user=user2, balance=Decimal("50.00"))
    wallet3 = Wallet(user=user3, balance=Decimal("25.00"))

    db_session.add_all([user1, user2,user3, wallet1, wallet2, wallet3])
    db_session.commit()

    tx1 = Transaction(from_wallet=wallet1, to_wallet=wallet2, amount=Decimal("10.00"))
    tx2 = Transaction(from_wallet=wallet1, to_wallet=wallet3, amount=Decimal("20.00"))
    
    db_session.add_all([tx1, tx2])
    db_session.commit()

    db_session.refresh(wallet1)
    assert len(wallet1.outgoing_transactions) == 2
    assert tx1 in wallet1.outgoing_transactions
    assert tx2 in wallet1.outgoing_transactions

    db_session.refresh(wallet2)
    db_session.refresh(wallet3)
    assert len(wallet2.outgoing_transactions) == 0
    assert len(wallet3.outgoing_transactions) == 0

    db_session.close()

    