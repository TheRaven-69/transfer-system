import logging
import random
import time

from app.core.celery_app import celery_app
from app.core.request_context import request_id_ctx
from app.core.settings import settings

logger = logging.getLogger(__name__)


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
):
    token = request_id_ctx.set(request_id)

    try:
        if settings.NOTIFY_DELAY_SEC > 0:
            time.sleep(settings.NOTIFY_DELAY_SEC)

        if random.random() < settings.NOTIFY_FAIL_RATE:
            raise RuntimeError("Simulated notification failure")

        logger.info(
            "notification_sent",
            extra={
                "extra_fields": {
                    "transfer_id": transfer_id,
                }
            },
        )

    except RuntimeError:
        log_fields = {
            "transfer_id": transfer_id,
            "retry_count": self.request.retries,
            "max_retries": self.max_retries,
        }
        if self.request.retries >= self.max_retries:
            logger.exception(
                "notification_failed",
                extra={"extra_fields": log_fields},
            )
        else:
            logger.warning(
                "notification_retry",
                extra={"extra_fields": log_fields},
            )
        raise

    finally:
        request_id_ctx.reset(token)
