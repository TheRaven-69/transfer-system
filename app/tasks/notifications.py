import logging
import secrets
import time

from app.core.celery_app import celery_app
from app.core.settings import settings

logger = logging.getLogger(__name__)
random = secrets.SystemRandom()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_transaction_notification(
    self,
    transfer_id: int,
    request_id: str | None = None,
    user_id: int | None = None,
    idempotency_fingerprint: str | None = None,
):
    request_id = request_id or "-"
    if settings.NOTIFY_DELAY_SEC > 0:
        time.sleep(settings.NOTIFY_DELAY_SEC)

    if random.random() < settings.NOTIFY_FAIL_RATE:  # nosec B311
        raise Exception("Simulated notification failure")

    logger.info(
        "Notification sent successfully: request_id=%s transfer_id=%s task_id=%s",
        request_id,
        transfer_id,
        self.request.id,
    )
