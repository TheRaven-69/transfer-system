import json
from contextlib import suppress
from functools import lru_cache
from typing import Any, Optional

from redis import Redis, RedisError

from config import CACHE_ENABLED, REDIS_URL


class Cache:
    """
    Cache abstraction.
    If Redis is disabled or fails, it behaves like a Null Object.
    """

    def __init__(self, client: Optional[Redis]):
        self._client = client

    def get(self, key: str, json_decode: bool = True) -> Optional[Any]:
        if not self._client:
            return None
        try:
            data = self._client.get(key)
            if not data:
                return None

            if isinstance(data, bytes):
                data = data.decode("utf-8")

            return json.loads(data) if json_decode else data
        except (RedisError, json.JSONDecodeError, TypeError):
            return None

    def set(
        self,
        key: str,
        value: Any,
        ex: int = 3600,
        nx: bool = False,
        json_encode: bool = True,
    ) -> bool:
        """Returns True if the key was set, False otherwise."""
        if not self._client:
            # If cache is disabled, we might want to return True or False
            # depending on the context. For idempotency, this is tricky.
            return False

        try:
            val = json.dumps(value) if json_encode else value
            return bool(self._client.set(key, val, ex=ex, nx=nx))
        except RedisError:
            return False

    def delete(self, key: str) -> None:
        if not self._client:
            return

        with suppress(RedisError):
            self._client.delete(key)


@lru_cache(maxsize=1)
def get_cache() -> Cache:
    if not CACHE_ENABLED:
        return Cache(None)

    try:
        client = Redis.from_url(REDIS_URL, decode_responses=True)
        return Cache(client)
    except Exception:
        # Fallback to Null Object if connection fails during init
        return Cache(None)
