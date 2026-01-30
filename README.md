Name project:
Wallet Transfers System
"Internal wallet service. Transfers between users"

Features:
    -Wallet per user(balance)
    -Transfer between users
    -No overdraft
    -Accurate money handing
    -Concurrency-safe operations

Core invariants:
    -Balance never < 0 
    -Double-entry for each operation is not equal to 0
    -Atomicity
    -Consistency under concurrency
    -Each transfer creates two transactions: a debit for the sender and a credit for the recipient.

Data model:
    -Users
    -Wallets
    -Transactions

API:
    POST /transfers

        body: from_user_id, to_user_id, amount

        errors: Недостатньо коштів (409)

        GET /wallets/{user_id} — balance

        GET /wallets/{user_id}/ledger — history 

Concurrency test scenario:
    -Initial balance: 100
    -10 conccurrent withdraw requests of 20
    -Expected: 5 success, 5 fail, final balance 0

Run locally:
    -Requirements: Python 3.13, Postgres
    -Next: Docker Compose(TODO)

