from prometheus_client import Counter, Gauge, Histogram

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
