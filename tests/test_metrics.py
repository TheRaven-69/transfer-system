from decimal import Decimal

from sqlalchemy.orm import sessionmaker

import app.core.metrics as metrics
import app.db.session as db_session
from app.db.models import Transaction, User, Wallet


def test_refresh_system_metrics_collects_real_totals(monkeypatch, engine, tables):
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    monkeypatch.setattr(db_session, "SessionLocal", session_local)

    with session_local() as db:
        users = [User(), User(), User()]
        db.add_all(users)
        db.commit()

        wallets = [
            Wallet(user_id=users[0].id, balance=Decimal("10.00")),
            Wallet(user_id=users[1].id, balance=Decimal("20.00")),
            Wallet(user_id=users[2].id, balance=Decimal("30.00")),
        ]
        db.add_all(wallets)
        db.commit()

        db.add_all(
            [
                Transaction(
                    from_wallet_id=wallets[0].id,
                    to_wallet_id=wallets[1].id,
                    amount=Decimal("5.00"),
                ),
                Transaction(
                    from_wallet_id=wallets[1].id,
                    to_wallet_id=wallets[2].id,
                    amount=Decimal("7.00"),
                ),
            ]
        )
        db.commit()

    metrics.refresh_system_metrics()

    assert metrics.WALLET_COUNT._value.get() == 3
    assert metrics.USER_COUNT._value.get() == 3
    assert metrics.TRANSACTION_COUNT._value.get() == 2
    assert metrics.LEDGER_BALANCE_TOTAL._value.get() == 60
    assert metrics.METRICS_COLLECTION_SUCCESS._value.get() == 1
