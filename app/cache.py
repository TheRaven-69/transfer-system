import json
import logging
from functools import lru_cache
from typing import Any, Optional

from redis import Redis, RedisError

from app.core.settings import settings

logger = logging.getLogger(__name__)


class Cache:
    """
    Cache abstraction.
    If Redis is disabled or fails, it behaves like a Null Object.
    """

    def __init__(self, client: Optional[Redis]):
        self._client = client

    def get(self, key: str, json_decode: bool = True) -> Optional[Any]:
        if not self._client:
            logger.debug(
                "cache_disabled",
                extra={"extra_fields": {"key": key}},
            )
            return None

        try:
            data = self._client.get(key)
            if not data:
                logger.warning(
                    "cache_miss",
                    extra={"extra_fields": {"key": key}},
                )
                return None

            if isinstance(data, bytes):
                data = data.decode("utf-8")

            return json.loads(data) if json_decode else data

        except RedisError:
            logger.warning(
                "redis_get_failed",
                extra={"extra_fields": {"key": key}},
                exc_info=True,
            )
            return None

        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "cache_decode_failed",
                extra={"extra_fields": {"key": key}},
                exc_info=True,
            )
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
            logger.warning(
                "redis_set_failed",
                extra={"extra_fields": {"key": key}},
                exc_info=True,
            )
            return False

    def delete(self, key: str) -> None:
        if not self._client:
            logger.debug(
                "cache_disabled",
                extra={"extra_fields": {"key": key}},
            )
            return

        try:
            self._client.delete(key)
        except RedisError:
            logger.warning(
                "redis_delete_failed",
                extra={"extra_fields": {"key": key}},
                exc_info=True,
            )


@lru_cache(maxsize=1)
def get_cache() -> Cache:
    if not settings.CACHE_ENABLED:
        return Cache(None)

    try:
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return Cache(client)
    except Exception:
        logger.warning("redis_init_failed", exc_info=True)
        return Cache(None)
