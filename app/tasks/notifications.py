import os
import random
import time

from app.core.celery_app import celery_app

NOTIFY_FAIL_RATE = float(os.getenv("NOTIFY_FAIL_RATE", "0"))


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_transaction_notification(self, transfer_id: int):
    time.sleep(2)

    if random.random() < NOTIFY_FAIL_RATE:
        raise Exception("Simulated notification failure")

    print(f"[notify] Notification sent for transfer_id={transfer_id}")
