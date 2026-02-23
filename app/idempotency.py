import hashlib
import json
from contextlib import contextmanager, suppress
from functools import lru_cache
from typing import Optional

from redis import Redis, RedisError

from app.services.exceptions import IdempotencyKeyConflict, RequestInProgress
from config import CACHE_ENABLED, REDIS_URL


class IdempotencyManager:
    """
    Handles idempotency.
    Ensures that retried requests with the same key but different payloads are rejected,
    and concurrent identical requests are blocked.
    """

    def __init__(self, client: Optional[Redis]):
        self._client = client
        self._ttl = 24 * 3600  # 24 hours default

    def _get_key(self, key: str) -> str:
        return f"idem:{key}"

    def check_and_reserve(self, key: str, payload_hash: str) -> None:
        """
        Atomically checks if a key exists and matches the payload hash.
        If it doesn't exist, reserves it.
        """
        if not self._client:
            # If idempotency storage is unavailable, we fail closed for safety
            raise RequestInProgress()

        redis_key = self._get_key(key)
        try:
            # Try to set the key only if it doesn't exist (NX)
            success = self._client.set(redis_key, payload_hash, ex=self._ttl, nx=True)

            if not success:
                existing_hash = self._client.get(redis_key)
                if isinstance(existing_hash, bytes):
                    existing_hash = existing_hash.decode("utf-8")

                if existing_hash and existing_hash != payload_hash:
                    raise IdempotencyKeyConflict()

                # Key exists and hash matches -> Request is already being processed or finished
                raise RequestInProgress()
        except RedisError:
            # On storage error, we fail closed to prevent accidental double-processing
            raise RequestInProgress() from None

    def remove_reservation(self, key: str) -> None:
        """Removes the idempotency key, usually called on transaction failure."""
        if not self._client:
            return
        with suppress(RedisError):
            self._client.delete(self._get_key(key))

    @contextmanager
    def reserve(self, key: str, payload_hash: str):
        """
        Context manager to handle idempotency reservation and automatic cleanup on failure.
        """
        self.check_and_reserve(key, payload_hash)
        try:
            yield
        except Exception:
            self.remove_reservation(key)
            raise


@lru_cache(maxsize=1)
def get_idempotency_manager() -> IdempotencyManager:
    if not CACHE_ENABLED:
        return IdempotencyManager(None)
    try:
        # We use a separate connection or the same URL,
        # but encapsulated in its own manager
        client = Redis.from_url(REDIS_URL, decode_responses=True)
        return IdempotencyManager(client)
    except Exception:
        return IdempotencyManager(None)


def hash_payload(data: dict) -> str:
    """Stable JSON hashing of a dictionary."""
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
