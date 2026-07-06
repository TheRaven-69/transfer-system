from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

import app.db.session as db_session
from app.core.metrics.collectors import (
    LEDGER_BALANCE_TOTAL,
    METRICS_COLLECTION_SUCCESS,
    SYSTEM_METRICS_COLLECTION_ERRORS_TOTAL,
    TRANSACTION_COUNT,
    USER_COUNT,
    WALLET_COUNT,
)
from app.db.models import Transaction, User, Wallet


def refresh_system_metrics() -> None:
    try:
        with db_session.SessionLocal() as db:
            wallet_count = db.execute(select(func.count(Wallet.id))).scalar_one()
            user_count = db.execute(select(func.count(User.id))).scalar_one()
            transaction_count = db.execute(
                select(func.count(Transaction.id))
            ).scalar_one()
            total_balance = db.execute(
                select(func.coalesce(func.sum(Wallet.balance), 0))
            ).scalar_one()
    except SQLAlchemyError:
        SYSTEM_METRICS_COLLECTION_ERRORS_TOTAL.inc()
        METRICS_COLLECTION_SUCCESS.set(0)
        return

    WALLET_COUNT.set(wallet_count)
    USER_COUNT.set(user_count)
    TRANSACTION_COUNT.set(transaction_count)
    LEDGER_BALANCE_TOTAL.set(float(total_balance))
    METRICS_COLLECTION_SUCCESS.set(1)
