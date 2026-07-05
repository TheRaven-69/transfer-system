import os
import sys
from pathlib import Path

import sentry_sdk
from fastapi.testclient import TestClient

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> None:
    if not os.getenv("SENTRY_DSN"):
        sys.exit("SENTRY_DSN must be set before running this verification script.")

    from app.core.celery_app import celery_app
    from app.core.settings import settings
    from app.main import app
    from app.tasks.notifications import send_transaction_notification

    def sentry_api_error():
        raise RuntimeError("Sentry API verification error")

    app.add_api_route(
        "/_verification/sentry-api-error",
        sentry_api_error,
        include_in_schema=False,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/_verification/sentry-api-error",
        headers={"X-Request-ID": "sentry-api-verification"},
    )
    if response.status_code != 500:
        raise RuntimeError(f"Expected API 500 response, got {response.status_code}")

    celery_app.conf.update(task_always_eager=True, task_eager_propagates=False)
    settings.NOTIFY_DELAY_SEC = 0
    settings.NOTIFY_FAIL_RATE = 1
    result = send_transaction_notification.apply(
        args=[42, "sentry-celery-verification", 7, "verification-fingerprint"]
    )
    if not result.failed():
        raise RuntimeError("Expected Celery verification task to fail")

    sentry_sdk.flush(timeout=10)
    print("Submitted API and Celery verification errors to Sentry.")


if __name__ == "__main__":
    main()
