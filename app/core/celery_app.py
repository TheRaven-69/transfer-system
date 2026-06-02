from celery import Celery  # type: ignore[import-untyped]

from app.core.settings import settings

celery_app = Celery(
    "transfer_system",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)
