from celery import Celery

from app.core.sentry import init_sentry
from app.core.settings import settings

init_sentry()

celery_app = Celery(
    "transfer_system",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications"],
)

celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)
