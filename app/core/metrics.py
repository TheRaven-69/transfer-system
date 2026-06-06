from decimal import Decimal

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

LEDGER_BALANCE_TOTAL = Gauge(
    "ledger_balance_total",
    "Current sum of all wallet balances",
)

LEDGER_EXPECTED_BALANCE_TOTAL = Gauge(
    "ledger_expected_balance_total",
    "Expected sum of all wallet balances based on initial wallet funding",
)

LEDGER_BALANCE_DELTA = Gauge(
    "ledger_balance_delta",
    "Difference between current and expected wallet balance totals",
)

LEDGER_METRICS_COLLECTION_ERRORS_TOTAL = Counter(
    "ledger_metrics_collection_errors_total",
    "Total number of failures while collecting ledger metrics",
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

INITIAL_WALLET_BALANCE = Decimal("100.00")


def refresh_ledger_metrics() -> None:
    from app.db.models import Wallet
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as db:
            total_balance, wallet_count = db.execute(
                select(
                    func.coalesce(func.sum(Wallet.balance), 0),
                    func.count(Wallet.id),
                )
            ).one()
    except SQLAlchemyError:
        LEDGER_METRICS_COLLECTION_ERRORS_TOTAL.inc()
        return

    current = Decimal(total_balance)
    expected = Decimal(wallet_count) * INITIAL_WALLET_BALANCE

    LEDGER_BALANCE_TOTAL.set(float(current))
    LEDGER_EXPECTED_BALANCE_TOTAL.set(float(expected))
    LEDGER_BALANCE_DELTA.set(float(current - expected))
