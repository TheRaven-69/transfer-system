from prometheus_client import Counter

WALLET_CACHE_HITS_TOTAL = Counter(
    "wallet_cache_hits_total",
    "Total number of wallet cache hits",
)

WALLET_CACHE_MISSES_TOTAL = Counter(
    "wallet_cache_misses_total",
    "Total number of wallet cache misses",
)


def record_wallet_cache_lookup(cache_hit: bool) -> None:
    if cache_hit:
        WALLET_CACHE_HITS_TOTAL.inc()
    else:
        WALLET_CACHE_MISSES_TOTAL.inc()
