import os
from redis import Redis
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "0") == "1"

_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    global _client

    if not CACHE_ENABLED:
        return None
    
    if _client is None:
        _client = Redis.from_url(REDIS_URL, decode_responses=True)

    return _client
