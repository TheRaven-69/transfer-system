# Transfer System API

Backend service for user accounts, wallets, and atomic wallet-to-wallet
transfers. The project combines authentication and resource ownership with
transaction safety, Redis idempotency, asynchronous notifications, monitoring,
Docker Compose, and Kubernetes manifests.

## Technology stack

- FastAPI and Pydantic
- SQLAlchemy 2.0 and Alembic
- PostgreSQL 15
- Redis
- RabbitMQ and Celery
- Nginx
- Prometheus, Grafana, Alertmanager, and Sentry
- Docker Compose and Kubernetes

## Features

- Registration with username, email, and password
- Login by username or email
- Scrypt password hashing with a random salt
- Short-lived JWT access tokens
- Rotating refresh tokens stored in an HttpOnly cookie
- Server-side refresh-token revocation and logout
- One wallet per user with an initial balance of `100.00`
- Ownership checks for profiles, wallets, and source wallets
- Atomic transfers with row locking
- Redis-backed idempotency protection
- Wallet cache and post-commit cache invalidation
- Celery notifications through RabbitMQ
- Request IDs, structured logging, metrics, and Sentry integration

## Architecture

```text
Client
  |
  v
Nginx -- rate limiting and gzip
  |
  v
FastAPI
  |-- PostgreSQL: users, wallets, transfers, refresh tokens
  |-- Redis: wallet cache and idempotency reservations
  `-- RabbitMQ --> Celery worker: transfer notifications
```

The application is split into API, use-case, service, persistence, and
infrastructure layers. API handlers parse HTTP input and dependencies; business
rules and transaction boundaries live in services and use cases.

## Authentication and authorization

Registration creates a user and wallet in one database transaction. Usernames
and email addresses are normalized to lowercase and must be unique.

Login accepts an `identifier`, which can contain either the username or email.
The response contains an access token. The refresh token is set as an HttpOnly,
SameSite=Lax cookie and is not returned in the JSON body.

Access rules:

- A user can read only their own profile.
- A user can read only their own wallet and balance.
- A user can transfer money only from their own wallet.
- The destination wallet can belong to another user.
- Requests without a valid access token return `401`.
- Attempts to access another user's resources return `403`.

Access tokens are stateless and are not stored in PostgreSQL. Only a SHA-256
hash of each refresh token is stored. Refreshing rotates and revokes the old
token; logout revokes the current refresh token.

## API

Interactive OpenAPI documentation is available at `/docs`.

| Method | Path | Authentication | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | Public | Create an account and wallet |
| `POST` | `/auth/login` | Public | Login by username or email |
| `POST` | `/auth/refresh` | Refresh cookie | Rotate refresh token |
| `POST` | `/auth/logout` | Refresh cookie | Revoke refresh token |
| `GET` | `/auth/me` | Bearer token | Read current account |
| `GET` | `/users/{user_id}` | Bearer token | Read own profile |
| `GET` | `/wallets/{wallet_id}` | Bearer token | Read own wallet |
| `POST` | `/transfers` | Bearer token | Transfer from own wallet |
| `GET` | `/health` | Public | Health check |
| `GET` | `/metrics` | Public | Prometheus metrics |

The old anonymous `POST /users` endpoint no longer exists. Account creation must
go through `/auth/register`.

### Registration

```bash
curl -X POST http://localhost:8081/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "correct-horse-battery-staple"
  }'
```

### Login

Use `-c cookies.txt` to store the refresh cookie locally:

```bash
curl -X POST http://localhost:8081/auth/login \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{
    "identifier": "alice",
    "password": "correct-horse-battery-staple"
  }'
```

Copy `access_token` from the response:

```bash
export ACCESS_TOKEN='paste-access-token-here'
```

### Read the current user

```bash
curl http://localhost:8081/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Transfer money

```bash
curl -X POST \
  'http://localhost:8081/transfers?from_wallet_id=1&to_wallet_id=2&amount=25.00' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: $(uuidgen)"
```

Every transfer attempt requires a unique `Idempotency-Key`. Reusing the same key
with the same request returns `409 Request in progress`; reusing it with a
different payload returns `409 Idempotency-Key conflict`.

### Refresh and logout

```bash
curl -X POST http://localhost:8081/auth/refresh -b cookies.txt -c cookies.txt
curl -X POST http://localhost:8081/auth/logout -b cookies.txt -c cookies.txt
```

## Environment configuration

Create a local environment file. The commands below target Git Bash:

```bash
cp .env.example .env
sed -i "s|^AUTH_JWT_SECRET=.*|AUTH_JWT_SECRET=$(openssl rand -hex 32)|" .env
```

Do not commit `.env`. It is excluded by both `.gitignore` and `.dockerignore`.

Important variables:

| Variable | Default/example | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL URL | Application and Alembic database |
| `REDIS_URL` | `redis://redis:6379/0` | Cache and idempotency store |
| `RABBITMQ_URL` | RabbitMQ URL | Celery broker |
| `AUTH_JWT_SECRET` | No safe default | JWT signing secret, at least 32 characters |
| `AUTH_ACCESS_TOKEN_MINUTES` | `15` | Access-token lifetime |
| `AUTH_REFRESH_TOKEN_DAYS` | `7` | Refresh-token lifetime |
| `AUTH_ISSUER` | `transfer-system` | JWT issuer |
| `CACHE_ENABLED` | `true` | Enable Redis cache/idempotency |
| `NOTIFY_FAIL_RATE` | `0.0` | Notification failure simulation |
| `SENTRY_DSN` | Empty | Optional Sentry project DSN |

Use a different JWT secret for every environment. In staging and production,
refresh cookies are also marked `Secure`.

## Run with Docker Compose

Build the application images:

```bash
docker compose build app worker
```

Start infrastructure first:

```bash
docker compose up -d db redis rabbitmq
```

Apply database migrations:

```bash
docker compose run --rm --no-deps app alembic upgrade head
```

Start the remaining services:

```bash
docker compose up -d
docker compose ps
```

Local endpoints:

- API through Nginx: <http://localhost:8081>
- OpenAPI docs: <http://localhost:8081/docs>
- RabbitMQ UI: <http://localhost:15672>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- Alertmanager: <http://localhost:9093>

Stop the environment without deleting PostgreSQL data:

```bash
docker compose down
```

## Database migrations

Alembic is the only mechanism used to create or update the runtime database.
The application no longer calls `Base.metadata.create_all()` at startup.

Create a revision after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the change"
```

Apply migrations locally:

```bash
alembic upgrade head
```

Check the current revision:

```bash
alembic current
```

For a database created before Alembic was introduced, mark the existing
pre-authentication schema once, then upgrade:

```bash
alembic stamp 20260830_01
alembic upgrade head
```

Do not run the stamp command on an empty database. A new database should use
only `alembic upgrade head`.

## Transfer guarantees

A transfer performs the following operations inside one database transaction:

1. Lock both wallets using `SELECT ... FOR UPDATE`.
2. Verify that both wallets exist.
3. Verify ownership of the source wallet.
4. Verify that the amount is positive and funds are sufficient.
5. Debit the source wallet.
6. Credit the destination wallet.
7. Insert the transaction record.
8. Commit all changes together.

If any step fails, the database transaction is rolled back. After a successful
commit, wallet cache entries are invalidated and a Celery notification is
published.

Redis reserves each idempotency key for 24 hours within the authenticated
user's namespace. Different users can safely submit the same client-generated
key. The service fails closed when the idempotency store is unavailable,
preventing an unprotected duplicate transfer.

## Testing and quality checks

Create and activate a virtual environment in Git Bash:

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the full test suite:

```bash
python -m pytest -q
```

Run static checks:

```bash
python -m ruff check app tests alembic
python -m ruff format --check app tests alembic
python -m mypy app
python -m bandit -r app -q
```

Tests cover authentication, username/email login, token rotation, logout,
ownership checks, migration upgrade/downgrade, atomic transfers, insufficient
funds, idempotency, caching, Celery context, metrics, and error handling.

The API load-test helper registers temporary users, logs each user in, and sends
every transfer with the source wallet owner's Bearer token. The generated load
accounts remain in the target database so their balances and transactions can be
inspected after a run; use a disposable environment for load testing.

## Kubernetes

Local Kubernetes manifests are stored in `k8s/`. They include PostgreSQL with a
PVC, Redis, RabbitMQ, the application, Celery worker, Nginx, HPA, KEDA, load-test
jobs, and a dedicated Alembic migration Job.

The migration Job must complete before the application and worker deployments
are rolled out. See [k8s/README.md](k8s/README.md) for the deployment sequence.

Docker Desktop Kubernetes must be enabled before using the local
`docker-desktop` context.

## Observability

The Compose environment includes Prometheus, Grafana, Alertmanager, PostgreSQL
exporter, Redis exporter, and RabbitMQ Prometheus metrics.

The provisioned dashboard covers request rate, error ratio, p95/p99 latency,
transfer throughput and amount, wallet cache behavior, ledger balance, database
latency, RabbitMQ queue depth, PostgreSQL connections, and Redis memory.

Alert rules cover API errors and latency, ledger consistency, database errors,
RabbitMQ backlog, and metric collection failures.

## Project structure

```text
alembic/                 Alembic environment and revisions
app/
  api/                   FastAPI routers and authentication dependency
  core/                  Settings, JWT/password security, logging, metrics
  db/                    SQLAlchemy models, session, transaction helpers
  schemas/               Request and response schemas
  services/              Authentication and business rules
  usecases/              Transfer and wallet orchestration
  tasks/                 Celery tasks
k8s/                     Kubernetes manifests and migration Job
nginx/                   Reverse-proxy configuration
observability/           Grafana and Prometheus configuration
tests/                   Unit and integration tests
```

## Security notes

- Never commit `.env`, `k8s/secrets.yaml`, private keys, or access tokens.
- Rotate `AUTH_JWT_SECRET` if it is exposed.
- Existing access tokens remain valid until expiration unless the signing secret
  is rotated.
- Logout revokes refresh tokens; it does not maintain an access-token denylist.
- Protect `/metrics` at the ingress or network layer in non-local environments.
- The included secrets and passwords in example files are placeholders for
  local development only.
