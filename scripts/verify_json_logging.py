"""Emit deterministic JSON logs for post-commit and cache failures.

Run inside the application container:
    python scripts/verify_json_logging.py

The script does not create business records and does not stop Redis. It uses a real
empty database transaction for the post-commit path and a synthetic Redis client
for the cache path.
"""

# ruff: noqa: E402 -- project imports require the repository root on sys.path.

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

from redis import Redis, RedisError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cache import Cache
from app.core.logging import setup_logging
from app.core.request_context import request_id_ctx
from app.core.settings import settings
from app.db.session import SessionLocal
from app.db.tx import on_commit, transaction_scope


class FailingRedis:
    def delete(self, _key: str) -> None:
        raise RedisError("simulated Redis delete failure")


def failing_post_commit_hook() -> None:
    raise RedisError("simulated post-commit Redis failure")


def verify_post_commit_logging() -> None:
    with SessionLocal() as db, transaction_scope(db):
        on_commit(db, failing_post_commit_hook)


def verify_cache_logging() -> None:
    cache = Cache(cast(Any, FailingRedis()))
    cache.delete("wallet:logging-verification")


def verify_real_redis_failures() -> None:
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    with SessionLocal() as db, transaction_scope(db):
        on_commit(db, redis_client.ping)

    Cache(redis_client).delete("wallet:logging-verification")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-redis",
        action="store_true",
        help="Use the configured Redis; intended while Redis is deliberately stopped.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()
    token = request_id_ctx.set("logging-verification")
    try:
        if args.real_redis:
            verify_real_redis_failures()
        else:
            verify_post_commit_logging()
            verify_cache_logging()
    finally:
        request_id_ctx.reset(token)


if __name__ == "__main__":
    main()
