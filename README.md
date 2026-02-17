# 💳 Transfer System API

High-level backend service for wallet management and atomic money transfers.

Built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, **Redis**, and **Docker**.  
Designed using clean architecture principles and production-oriented patterns.

---

## 🚀 Core Features

- User creation
- Wallet creation with initial balance
- Atomic wallet-to-wallet transfers
- Custom domain exceptions
- Redis caching (wallet read optimization)
- Transaction-safe balance updates
- Dockerized environment
- CI pipeline with GitHub Actions
- Structured layered architecture

---

## 🏗 Architecture Overview

The system follows layered architecture with strict separation of concerns:

- **API Layer** → HTTP request handling & validation
- **Service Layer** → Business logic & domain rules
- **Persistence Layer** → Database models & sessions
- **Infrastructure Layer** → Redis, Docker, CI/CD

---

## 📐 Architecture Diagram

             ┌────────────────────┐
             │      Client        │
             │   (HTTP Request)   │
             └─────────┬──────────┘
                       │
                       ▼
             ┌────────────────────┐
             │   FastAPI Router   │
             │  (Thin Controller) │
             └─────────┬──────────┘
                       │
                       ▼
             ┌────────────────────┐
             │    Service Layer   │
             │  Business Logic    │
             │  Atomic Transfers  │
             └─────────┬──────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌──────────────────┐         ┌──────────────────┐
│ PostgreSQL (DB)  │         │ Redis (Cache)    │
│ Users / Wallets  │         │ Wallet Snapshot  │
│ Transfers        │         │ Read Optimization│
└──────────────────┘         └──────────────────┘



---

## 🔁 Transfer Flow

1. API receives transfer request
2. Router validates input and forwards to service layer
3. Service layer:
   - Validates wallets existence
   - Checks sufficient balance
   - Executes atomic database transaction
4. Database commit
5. Redis cache refresh
6. Response returned

All transfer operations are executed inside a single database transaction to guarantee consistency.

---

## 🧠 Design Decisions

### 🔹 Thin Routers
Routers handle only:
- Request parsing
- Dependency injection
- Response formatting

No business logic inside controllers.

---

### 🔹 Service Isolation
All domain logic is located inside `/services`.

Examples:
- `create_transfer`
- `get_wallet`
- `create_wallet_for_user`

---

### 🔹 Custom Exceptions

Domain-level exceptions:

- `WalletNotFound`
- `UserNotFound`
- `InsufficientFunds`
- `Conflict`

Mapped globally via FastAPI exception handlers.

---

### 🔹 Transaction Safety

Transfers are wrapped inside a database transaction:

- Debit source wallet
- Credit target wallet
- Create transfer record
- Commit

Prevents:
- Partial updates
- Inconsistent balances
- Data corruption

---

### 🔹 Redis Caching Strategy

- Wallet object stored in cache
- On read → check cache first
- On update → invalidate or refresh cache

Improves performance and reduces database load.

---

## 🧪 Testing

Test coverage includes:

- Wallet creation
- Successful transfer
- Insufficient funds scenario
- Not found scenarios
- Dependency override for DB session


## 📂 Project Structure

app/
 ├── api/
 │   ├── users.py
 │   ├── wallets.py
 │   └── transfers.py
 │
 ├── services/
 │   ├── users.py
 │   ├── wallets.py
 │   ├── transfers.py
 │   └── exceptions.py
 │
 ├── db/
 │   ├── models.py
 │   ├── session.py
 │
 ├── cache/
 │   └── redis.py
 │
 └── main.py

tests/
 ├── test_wallets.py
 ├── test_transfers.py
 └── conftest.py
