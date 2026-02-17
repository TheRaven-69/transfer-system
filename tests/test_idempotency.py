from sqlalchemy import select, func
from app.db.models import Transaction


def test_idempotency_same_key_returns_same_transaction(client, db, seeded_wallets):
    w1, w2 = seeded_wallets
    headers = {"Idempotency-Key": "abc-123"}

    r1 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r1.status_code == 200
    tx1 = r1.json()

    r2 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r2.status_code == 200
    tx2 = r2.json()

    assert tx2["id"] == tx1["id"]

    count = db.execute(select(func.count(Transaction.id))).scalar_one()
    assert count == 1


def test_idempotency_same_key_different_payload_conflict(client, seeded_wallets):
    w1, w2 = seeded_wallets
    headers = {"Idempotency-Key": "abc-999"}

    r1 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "10.00"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/transfers",
        params={"from_wallet_id": w1.id, "to_wallet_id": w2.id, "amount": "20.00"},
        headers=headers,
    )
    assert r2.status_code == 409
