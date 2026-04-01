from prometheus_client import Counter, Histogram

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
