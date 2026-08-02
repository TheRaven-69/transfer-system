from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

import app.core.metrics as metrics
import app.db.session as db_session
from app.core.metrics import system as system_metrics
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


def test_refresh_system_metrics_logs_database_error(monkeypatch, caplog):
    class FailingSession:
        def __enter__(self):
            raise SQLAlchemyError("metrics database unavailable")

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(db_session, "SessionLocal", FailingSession)

    with caplog.at_level("WARNING"):
        system_metrics.refresh_system_metrics()

    record = next(
        record
        for record in caplog.records
        if record.message == "system_metrics_collection_failed"
    )
    assert record.exc_info is not None
    assert record.exc_info[0] is SQLAlchemyError
    assert str(record.exc_info[1]) == "metrics database unavailable"
