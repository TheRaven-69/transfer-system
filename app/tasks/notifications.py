import random
import time

from app.core.celery_app import celery_app
from app.core.settings import settings


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_transaction_notification(self, transfer_id: int):
    if settings.NOTIFY_DELAY_SEC > 0:
        time.sleep(settings.NOTIFY_DELAY_SEC)

    if random.random() < settings.NOTIFY_FAIL_RATE:
        raise Exception("Simulated notification failure")

    print(f"[notify] Notification sent for transfer_id={transfer_id}")
