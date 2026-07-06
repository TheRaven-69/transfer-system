import app.db.session as db_session
from app.core.metrics.cache import (
    WALLET_CACHE_HITS_TOTAL,
    WALLET_CACHE_MISSES_TOTAL,
    record_wallet_cache_lookup,
)
from app.core.metrics.collectors import (
    DB_QUERY_DURATION_SECONDS,
    DB_QUERY_ERRORS_TOTAL,
    HTTP_EXCEPTIONS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUEST_OUTCOMES_TOTAL,
    HTTP_REQUESTS_TOTAL,
    LEDGER_BALANCE_TOTAL,
    METRICS_COLLECTION_SUCCESS,
    SYSTEM_METRICS_COLLECTION_ERRORS_TOTAL,
    TRANSACTION_COUNT,
    TRANSFER_AMOUNT_TOTAL,
    TRANSFERS_CREATED_TOTAL,
    USER_COUNT,
    WALLET_COUNT,
)
from app.core.metrics.db import register_db_metrics
from app.core.metrics.system import refresh_system_metrics

register_db_metrics(db_session.engine)

__all__ = [
    "DB_QUERY_DURATION_SECONDS",
    "DB_QUERY_ERRORS_TOTAL",
    "HTTP_EXCEPTIONS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUEST_OUTCOMES_TOTAL",
    "HTTP_REQUESTS_TOTAL",
    "LEDGER_BALANCE_TOTAL",
    "METRICS_COLLECTION_SUCCESS",
    "SYSTEM_METRICS_COLLECTION_ERRORS_TOTAL",
    "TRANSACTION_COUNT",
    "TRANSFER_AMOUNT_TOTAL",
    "TRANSFERS_CREATED_TOTAL",
    "USER_COUNT",
    "WALLET_CACHE_HITS_TOTAL",
    "WALLET_CACHE_MISSES_TOTAL",
    "WALLET_COUNT",
    "record_wallet_cache_lookup",
    "refresh_system_metrics",
]
