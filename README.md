💳 Transfer System API

Production-ready wallet & money transfer service built with:

FastAPI • SQLAlchemy 2.0 • PostgreSQL • Redis • RabbitMQ • Celery •
Nginx • Docker

Designed using layered architecture and production-oriented backend
patterns.

============================================================

🚀 CORE FEATURES

-   User creation
-   Wallet creation with initial balance
-   Atomic wallet-to-wallet transfers
-   Redis wallet caching (read optimization)
-   Idempotency-Key support (24h TTL)
-   Async notifications via Celery
-   Retry & backoff strategy
-   Reverse proxy with rate limiting
-   Fully containerized infrastructure (6 services)
-   CI pipeline with GitHub Actions

============================================================

🏗 SYSTEM ARCHITECTURE

Multi-service Docker environment:

-   App — FastAPI (business logic)
-   PostgreSQL — primary database
-   Redis — balance cache + idempotency store
-   RabbitMQ — message broker
-   Celery Worker — async task processing
-   Nginx — reverse proxy + rate limiting

------------------------------------------------------------------------

📐 HIGH-LEVEL FLOW

Client │ ▼ Nginx (rate limit, gzip) │ ▼ FastAPI │ ├── PostgreSQL (atomic
transaction) ├── Redis (cache + idempotency) └── RabbitMQ → Celery
Worker

============================================================

🔁 TRANSFER FLOW (PRODUCTION FLOW)

1.  Client sends POST /transfers with Idempotency-Key
2.  Nginx applies rate limiting
3.  FastAPI:
    -   Validates request
    -   Checks idempotency store (Redis)
4.  Service layer:
    -   Validates wallet existence
    -   Checks balance
    -   Executes atomic DB transaction
5.  Database commit
6.  Redis cache invalidation
7.  Async notification task published to RabbitMQ
8.  Celery worker processes notification (retry/backoff)
9.  Response returned (cached for idempotent retries)

============================================================

🧠 ARCHITECTURAL PRINCIPLES

🔹 Layered Architecture

-   API Layer → HTTP interface
-   Service Layer → Business logic
-   Persistence Layer → ORM & DB
-   Infrastructure Layer → Redis, Broker, Docker

------------------------------------------------------------------------

🔹 Thin Controllers

Routers handle only: - Parsing - Dependency injection - Response
formatting

All domain logic lives inside /services.

------------------------------------------------------------------------

🔹 Atomic Transfers

Each transfer is wrapped inside a single database transaction:

-   Debit source wallet
-   Credit target wallet
-   Insert transfer record
-   Commit

Guarantees: - No partial updates - No race-condition corruption -
Consistent balances

------------------------------------------------------------------------

🔹 Redis Strategy

Wallet Read Optimization:

GET /wallet/{id}:

1.  Check Redis
2.  If miss → fetch from DB
3.  Cache result

Target: 80–90% reduction of read load on PostgreSQL

------------------------------------------------------------------------

🔹 Idempotency-Key

-   Client provides UUID
-   Result stored in Redis (TTL 24h)
-   Repeated request returns identical response
-   Lock mechanism prevents race condition

Ensures safe retries in distributed environments.

------------------------------------------------------------------------

🔹 Async Notifications

After successful transfer:

-   Task published to RabbitMQ
-   Processed by Celery worker
-   Retry & backoff enabled
-   Failure simulation via NOTIFY_FAIL_RATE

------------------------------------------------------------------------

🔹 Nginx Reverse Proxy

Configured with:

-   Rate limiting on POST /transfers
-   Gzip compression
-   Proxy buffers
-   Timeout hierarchy: Nginx > FastAPI > DB statement_timeout

============================================================

🐳 DOCKER INFRASTRUCTURE

Services:

app db redis rabbitmq worker nginx

------------------------------------------------------------------------

Run Project:

docker-compose up –build

Access:

API → http://localhost Docs → http://localhost/docs RabbitMQ UI →
http://localhost:15672

============================================================

🧪 TESTING

pytest

Test coverage includes:

-   Wallet creation
-   Successful transfer
-   Insufficient funds
-   Idempotency behavior
-   Cache invalidation
-   Exception handling
-   Dependency overrides

============================================================

📂 PROJECT STRUCTURE

app/ ├── api/ │ ├── users.py │ ├── wallets.py │ ├── transfers.py │ ├──
services/ │ ├── users.py │ ├── wallets.py │ ├── transfers.py │ └──
exceptions.py │ ├── tasks/ │ └── notifications.py │ ├── db/ │ ├──
models.py │ ├── session.py │ ├── cache.py ├── main.py

docker-compose.yml nginx.conf

============================================================

📈 PRODUCTION-ORIENTED PATTERNS IMPLEMENTED

-   Idempotent API design
-   Cache invalidation strategy
-   Transaction-safe state updates
-   Async task queue
-   Reverse proxy hardening
-   Containerized microservice architecture
-   CI integration

============================================================

🎯 PROJECT PURPOSE

This project demonstrates:

-   High-load readiness patterns
-   Clean architecture separation
-   Infrastructure orchestration
-   Production-level API behavior

============================================================
