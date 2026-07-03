from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total number of HTTP requests", ["method", "path", "status"]
)

HTTP_REQUEST_OUTCOMES_TOTAL = Counter(
    "http_request_outcomes_total",
    "Total number of HTTP requests grouped by outcome",
    ["method", "path", "outcome"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

HTTP_EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total",
    "Total number of handled HTTP exceptions",
    ["method", "path", "status", "exception_type"],
)

TRANSFERS_CREATED_TOTAL = Counter(
    "transfers_created_total",
    "Total number of successfully created transfers",
)

TRANSFER_AMOUNT_TOTAL = Counter(
    "transfer_amount_total",
    "Total monetary amount of successfully created transfers",
)

WALLET_CACHE_HITS_TOTAL = Counter(
    "wallet_cache_hits_total",
    "Total number of wallet cache hits",
)

WALLET_CACHE_MISSES_TOTAL = Counter(
    "wallet_cache_misses_total",
    "Total number of wallet cache misses",
)

WALLET_COUNT = Gauge(
    "wallet_count",
    "Current number of wallets",
)

USER_COUNT = Gauge(
    "user_count",
    "Current number of users",
)

TRANSACTION_COUNT = Gauge(
    "transaction_count",
    "Current number of transactions",
)

LEDGER_BALANCE_TOTAL = Gauge(
    "ledger_balance_total",
    "Current sum of all wallet balances",
)

METRICS_COLLECTION_SUCCESS = Gauge(
    "metrics_collection_success",
    "Whether the latest system metrics collection succeeded",
)

SYSTEM_METRICS_COLLECTION_ERRORS_TOTAL = Counter(
    "system_metrics_collection_errors_total",
    "Total number of failures while collecting system metrics",
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
)

DB_QUERY_ERRORS_TOTAL = Counter(
    "db_query_errors_total",
    "Total number of database query errors",
    ["operation"],
)


def refresh_system_metrics() -> None:
    from app.db.models import Transaction, User, Wallet
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as db:
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
