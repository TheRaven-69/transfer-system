from typing import Optional
from redis import Redis

from config import CACHE_ENABLED, REDIS_URL

_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    global _client

    if not CACHE_ENABLED:
        return None
    
    if _client is None:
        _client = Redis.from_url(REDIS_URL, decode_responses=True)

    return _client
