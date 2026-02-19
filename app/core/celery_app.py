from celery import Celery
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "transfer_system",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.notifications"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1
)
