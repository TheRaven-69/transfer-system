import inspect

import sentry_sdk
from celery import Celery, signals

from app.core.request_context import request_id_ctx
from app.core.sentry import init_sentry, set_transfer_context
from app.core.settings import settings

init_sentry()

celery_app = Celery(
    "transfer_system",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications"],
)

celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)


def _task_metadata(task, args, kwargs) -> dict:
    try:
        return inspect.signature(task.run).bind_partial(*args, **kwargs).arguments
    except (AttributeError, TypeError):
        return dict(kwargs)


def set_sentry_task_context(task, task_id, args, kwargs) -> None:
    metadata = _task_metadata(task, args, kwargs)
    request_id = metadata.get("request_id") or "-"
    transfer_id = metadata.get("transfer_id")
    user_id = metadata.get("user_id")
    idempotency_fingerprint = metadata.get("idempotency_fingerprint")

    sentry_sdk.set_tag("component", "celery")
    sentry_sdk.set_tag("task_name", task.name)
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
            "task_id": task_id,
            "retries": task.request.retries,
        },
    )


@signals.task_prerun.connect
def task_prerun_handler(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    **_extra,
):
    task = task or sender
    if task is None:
        return

    args = args or ()
    kwargs = kwargs or {}
    request_id = _task_metadata(task, args, kwargs).get("request_id") or "-"
    task.request.request_id_ctx_token = request_id_ctx.set(request_id)
    set_sentry_task_context(task, task_id, args, kwargs)


@signals.task_postrun.connect
def task_postrun_handler(sender=None, task=None, **_extra):
    task = task or sender
    if task is None:
        return

    token = getattr(task.request, "request_id_ctx_token", None)
    if token is not None:
        request_id_ctx.reset(token)
        task.request.request_id_ctx_token = None
