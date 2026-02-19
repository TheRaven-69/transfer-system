import os
from typing import Optional


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    return float(value)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./app.db")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = _as_bool(os.getenv("CACHE_ENABLED"), default=False)

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

NOTIFY_FAIL_RATE = _as_float(os.getenv("NOTIFY_FAIL_RATE"), default=0.0)
NOTIFY_DELAY_SEC = _as_float(os.getenv("NOTIFY_DELAY_SEC"), default=2.0)
