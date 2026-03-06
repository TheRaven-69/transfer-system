from app.core.settings import settings

DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
CACHE_ENABLED = settings.CACHE_ENABLED

# canonical
RABBITMQ_URL = settings.RABBITMQ_URL

NOTIFY_FAIL_RATE = settings.NOTIFY_FAIL_RATE
NOTIFY_DELAY_SEC = settings.NOTIFY_DELAY_SEC

# backward compat exports (temporary for PR1)
CELERY_BROKER_URL = settings.RABBITMQ_URL
CELERY_RESULT_BACKEND = settings.REDIS_URL
