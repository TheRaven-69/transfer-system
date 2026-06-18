import logging
import random
import time

import sentry_sdk

from app.core.celery_app import celery_app
from app.core.request_context import request_id_ctx
from app.core.sentry import set_transfer_context
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
    user_id: int | None = None,
    idempotency_fingerprint: str | None = None,
):
    request_id = request_id or "-"

    token = request_id_ctx.set(request_id)

    sentry_sdk.set_tag("component", "celery")
    sentry_sdk.set_tag("task_name", self.name)
    set_transfer_context(
        transfer_id=transfer_id,
        user_id=user_id,
        idempotency_fingerprint=idempotency_fingerprint,
    )
    sentry_sdk.set_context(
        "celery_task",
        {
            "request_id": request_id,
            "transfer_id": transfer_id,
            "task_id": self.request.id,
            "retries": self.request.retries,
        },
    )

    try:
        if settings.NOTIFY_DELAY_SEC > 0:
            time.sleep(settings.NOTIFY_DELAY_SEC)

        if random.random() < settings.NOTIFY_FAIL_RATE:
            raise Exception("Simulated notification failure")

        logger.info(
            "Notification sent successfully: request_id=%s transfer_id=%s task_id=%s",
            request_id,
            transfer_id,
            self.request.id,
        )
    finally:
        request_id_ctx.reset(token)
