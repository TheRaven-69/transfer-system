"""Load test helper for the transfer system.

Examples:
    python scripts/load_test.py api --base-url http://transfer-nginx --requests 500
    python scripts/load_test.py task-only --requests 5000 --concurrency 50
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BASE_URL = "http://localhost:8080"


@dataclass(frozen=True)
class WalletRef:
    id: int
    user_id: int


@dataclass(frozen=True)
class RequestResult:
    status_code: int
    elapsed: float
    detail: str = ""


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * pct)
    return sorted_values[index]


def build_idempotency_key(prefix: str, index: int) -> str:
    return f"{prefix}-{index}-{uuid.uuid4()}"


async def create_user(client: httpx.AsyncClient) -> WalletRef:
    response = await client.post("/users")
    response.raise_for_status()
    user_id = int(response.json()["id"])

    response = await client.get(f"/users/{user_id}")
    response.raise_for_status()
    data = response.json()

    return WalletRef(id=int(data["wallet"]["id"]), user_id=user_id)


async def seed_wallets(
    client: httpx.AsyncClient, users: int, concurrency: int
) -> list[WalletRef]:
    semaphore = asyncio.Semaphore(concurrency)

    async def create_one() -> WalletRef:
        async with semaphore:
            return await create_user(client)

    return await asyncio.gather(*(create_one() for _ in range(users)))


def choose_transfer_wallets(wallets: list[WalletRef], index: int) -> tuple[int, int]:
    from_index = index % len(wallets)
    to_index = (from_index + 1) % len(wallets)

    if index % 2:
        from_index, to_index = to_index, from_index

    return wallets[from_index].id, wallets[to_index].id


async def post_transfer(
    client: httpx.AsyncClient,
    wallets: list[WalletRef],
    amount: Decimal,
    index: int,
    key_prefix: str,
    rps: float,
) -> RequestResult:
    if rps > 0:
        await asyncio.sleep(index / rps)

    from_wallet_id, to_wallet_id = choose_transfer_wallets(wallets, index)
    started = time.perf_counter()

    try:
        response = await client.post(
            "/transfers",
            params={
                "from_wallet_id": from_wallet_id,
                "to_wallet_id": to_wallet_id,
                "amount": str(amount),
            },
            headers={
                "Idempotency-Key": build_idempotency_key(key_prefix, index),
                "X-Request-ID": f"load-{key_prefix}-{index}",
            },
        )
        elapsed = time.perf_counter() - started

        detail = response.text[:200] if response.status_code >= 400 else ""
        return RequestResult(response.status_code, elapsed, detail)
    except httpx.HTTPError as exc:
        elapsed = time.perf_counter() - started
        return RequestResult(0, elapsed, str(exc))


async def run_api_load(args: argparse.Namespace) -> list[RequestResult]:
    limits = httpx.Limits(
        max_connections=args.concurrency + args.seed_concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)

    async with httpx.AsyncClient(
        base_url=args.base_url,
        limits=limits,
        timeout=timeout,
    ) as client:
        health = await client.get("/health")
        health.raise_for_status()

        print(f"Seeding {args.users} users/wallets through {args.base_url} ...")
        wallets = await seed_wallets(client, args.users, args.seed_concurrency)
        print(f"Seeded wallets: {', '.join(str(wallet.id) for wallet in wallets[:8])}")

        semaphore = asyncio.Semaphore(args.concurrency)
        key_prefix = args.key_prefix or f"load-{uuid.uuid4().hex[:8]}"

        async def one(index: int) -> RequestResult:
            async with semaphore:
                return await post_transfer(
                    client=client,
                    wallets=wallets,
                    amount=args.amount,
                    index=index,
                    key_prefix=key_prefix,
                    rps=args.rps,
                )

        return await asyncio.gather(*(one(i) for i in range(args.requests)))


def publish_task(index: int) -> RequestResult:
    started = time.perf_counter()
    try:
        from app.tasks.notifications import send_transaction_notification

        send_transaction_notification.delay(index)
        return RequestResult(202, time.perf_counter() - started)
    except Exception as exc:
        return RequestResult(0, time.perf_counter() - started, str(exc))


async def run_task_only_load(args: argparse.Namespace) -> list[RequestResult]:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@postgres:5432/transfer_db",
    )
    os.environ["RABBITMQ_URL"] = args.rabbitmq_url or os.getenv(
        "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"
    )
    os.environ["REDIS_URL"] = args.redis_url or os.getenv(
        "REDIS_URL", "redis://redis:6379/0"
    )

    semaphore = asyncio.Semaphore(args.concurrency)

    async def one(index: int) -> RequestResult:
        async with semaphore:
            return await asyncio.to_thread(publish_task, index)

    return await asyncio.gather(*(one(i) for i in range(args.requests)))


def print_summary(results: list[RequestResult], total_elapsed: float) -> None:
    status_counts = Counter(result.status_code for result in results)
    successful = sum(
        count for status, count in status_counts.items() if 200 <= status < 300
    )
    failed = len(results) - successful
    latencies = [result.elapsed for result in results]
    error_samples = [
        result
        for result in results
        if result.status_code >= 400 or result.status_code == 0
    ]

    print()
    print("Load test summary")
    print("=================")
    print(f"Total requests: {len(results)}")
    print(f"Successful:     {successful}")
    print(f"Failed:         {failed}")
    print(f"Elapsed:        {total_elapsed:.2f}s")
    print(f"Throughput:     {len(results) / total_elapsed:.2f} req/s")
    print(f"Status codes:   {dict(sorted(status_counts.items()))}")
    print()
    print("Latency")
    print(f"  avg: {statistics.mean(latencies):.4f}s")
    print(f"  p50: {percentile(latencies, 0.50):.4f}s")
    print(f"  p95: {percentile(latencies, 0.95):.4f}s")
    print(f"  p99: {percentile(latencies, 0.99):.4f}s")
    print(f"  max: {max(latencies):.4f}s")

    if error_samples:
        print()
        print("Error samples")
        for sample in error_samples[:5]:
            print(
                f"  status={sample.status_code} elapsed={sample.elapsed:.4f}s {sample.detail}"
            )


def parse_decimal(value: str) -> Decimal:
    amount = Decimal(value)
    if amount <= 0:
        raise argparse.ArgumentTypeError("amount must be greater than zero")
    return amount


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load test transfer API and Celery worker paths."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    api = subparsers.add_parser(
        "api",
        help="Load the public API path: Nginx/FastAPI/DB/Redis/RabbitMQ/Celery.",
    )
    api.add_argument("--base-url", default=DEFAULT_BASE_URL)
    api.add_argument("--requests", type=int, default=500)
    api.add_argument("--concurrency", type=int, default=25)
    api.add_argument("--users", type=int, default=20)
    api.add_argument("--seed-concurrency", type=int, default=5)
    api.add_argument("--amount", type=parse_decimal, default=Decimal("0.01"))
    api.add_argument("--timeout", type=float, default=10.0)
    api.add_argument("--key-prefix", default="")
    api.add_argument(
        "--rps",
        type=float,
        default=0.0,
        help="Optional request rate. Use 20 or less when going through Nginx.",
    )

    task_only = subparsers.add_parser(
        "task-only",
        help="Publish Celery notification tasks directly to RabbitMQ.",
    )
    task_only.add_argument("--requests", type=int, default=1000)
    task_only.add_argument("--concurrency", type=int, default=50)
    task_only.add_argument("--rabbitmq-url", default="")
    task_only.add_argument("--redis-url", default="")

    return parser


async def run(args: argparse.Namespace) -> list[RequestResult]:
    if args.mode == "api":
        return await run_api_load(args)
    if args.mode == "task-only":
        return await run_task_only_load(args)
    raise ValueError(f"Unknown mode: {args.mode}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    started = time.perf_counter()
    results = asyncio.run(run(args))
    print_summary(results, time.perf_counter() - started)


if __name__ == "__main__":
    main()
