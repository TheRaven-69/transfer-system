import hashlib

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.settings import settings

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "idempotency-key",
    "idempotency_key",
}
_sentry_initialized = False


def _mask_sensitive_data(data):
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                cleaned[key] = "[Filtered]"
            else:
                cleaned[key] = _mask_sensitive_data(value)
        return cleaned

    if isinstance(data, list):
        return [_mask_sensitive_data(item) for item in data]

    return data


def before_send(event, hint):
    return _mask_sensitive_data(event)


def before_send_transaction(event, hint):
    cleaned = _mask_sensitive_data(event)

    for span in cleaned.get("spans", []):
        if "redis" not in span.get("op", "").lower():
            continue

        description = span.get("description")
        if description:
            command = description.split(maxsplit=1)[0]
            span["description"] = f"{command} [Filtered]"

    return cleaned


def traces_sampler(sampling_context):
    transaction_context = sampling_context.get("transaction_context", {})
    transaction_name = transaction_context.get("name", "")

    if transaction_name.rstrip("/").endswith("/health"):
        return 0.0

    parent_sampled = sampling_context.get("parent_sampled")
    if parent_sampled is not None:
        return parent_sampled

    return settings.SENTRY_TRACES_SAMPLE_RATE


def idempotency_key_fingerprint(idempotency_key: str) -> str:
    return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]


def set_transfer_context(
    *,
    transfer_id: int | None = None,
    user_id: int | None = None,
    idempotency_key: str | None = None,
    idempotency_fingerprint: str | None = None,
) -> None:
    context = {}

    if transfer_id is not None:
        context["transfer_id"] = transfer_id
    if user_id is not None:
        context["user_id"] = user_id
        sentry_sdk.set_user({"id": str(user_id)})
    if context:
        sentry_sdk.set_context("transfer", context)

    if idempotency_key:
        idempotency_fingerprint = idempotency_key_fingerprint(idempotency_key)
    if idempotency_fingerprint:
        sentry_sdk.set_context(
            "idempotency",
            {"key_fingerprint": idempotency_fingerprint},
        )


def init_sentry() -> None:
    global _sentry_initialized

    if _sentry_initialized or not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        environment=settings.SENTRY_ENVIRONMENT or settings.APP_ENV,
        release=settings.SENTRY_RELEASE,
        traces_sampler=traces_sampler,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=before_send,
        before_send_transaction=before_send_transaction,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
    )
    _sentry_initialized = True
