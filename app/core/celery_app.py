from celery import Celery

from app.core.settings import settings

celery_app = Celery(
    "transfer_system",
    broker=str(settings.RABBITMQ_URL),
    backend=str(settings.REDIS_URL),
)

celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)
