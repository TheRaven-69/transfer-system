from app.core.request_context import request_id_ctx
from app.tasks.notifications import send_transaction_notification


def enqueue_transfer_notification(
    transfer_id: int,
    user_id: int | None = None,
    idempotency_fingerprint: str | None = None,
) -> None:
    send_transaction_notification.delay(
        transfer_id,
        request_id_ctx.get(),
        user_id,
        idempotency_fingerprint,
    )
