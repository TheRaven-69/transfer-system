from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

import app.core.sentry as sentry
import app.services.transfers as transfers_service
import app.tasks.notifications as notifications
from app.core import celery_app, middleware
from app.core.middleware import _sentry_user_from_request_state
from app.core.request_context import request_id_ctx
from app.core.settings import SentrySettings
from app.idempotency import idempotency_key_fingerprint


def test_before_send_masks_sensitive_values():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer secret",
                "Idempotency-Key": "raw-key",
                "X-Request-ID": "request-1",
            }
        }
    }

    cleaned = sentry.before_send(event, {})

    assert cleaned["request"]["headers"]["Authorization"] == "[Filtered]"
    assert cleaned["request"]["headers"]["Idempotency-Key"] == "[Filtered]"
    assert cleaned["request"]["headers"]["X-Request-ID"] == "request-1"


def test_before_send_masks_nested_sensitive_values():
    event = {
        "extra": {
            "user": {
                "email": "user@example.com",
                "password": "secret",
                "profile": {"apiSecret": "nested-secret"},
            },
            "auth": [{"refreshToken": "raw-token"}],
        }
    }

    cleaned = sentry.before_send(event, {})

    user = cleaned["extra"]["user"]
    assert user["email"] == "user@example.com"
    assert user["password"] == "[Filtered]"
    assert user["profile"]["apiSecret"] == "[Filtered]"
    assert cleaned["extra"]["auth"][0]["refreshToken"] == "[Filtered]"


def test_before_send_masks_extended_sensitive_keys(monkeypatch):
    monkeypatch.setattr(sentry.settings.sentry, "extra_sensitive_keys", {"credential"})

    event = {
        "extra": {
            "service": {
                "apiCredential": "raw-credential",
                "name": "ledger",
            }
        }
    }

    cleaned = sentry.before_send(event, {})

    assert cleaned["extra"]["service"]["apiCredential"] == "[Filtered]"
    assert cleaned["extra"]["service"]["name"] == "ledger"


def test_before_send_transaction_masks_redis_span_description():
    event = {
        "spans": [
            {"op": "db.redis", "description": "SET idem:transfer:raw-key value"},
            {"op": "db.sql.query", "description": "SELECT * FROM wallets"},
        ]
    }

    cleaned = sentry.before_send_transaction(event, {})

    assert cleaned["spans"][0]["description"] == "SET [Filtered]"
    assert cleaned["spans"][1]["description"] == "SELECT * FROM wallets"


def test_traces_sampler_excludes_health_and_respects_parent(monkeypatch):
    monkeypatch.setattr(sentry.settings.sentry, "traces_sample_rate", 0.25)

    assert (
        sentry.traces_sampler({"transaction_context": {"name": "GET /health"}}) == 0.0
    )
    assert (
        sentry.traces_sampler(
            {
                "transaction_context": {"name": "app.tasks.notify"},
                "parent_sampled": True,
            }
        )
        is True
    )
    assert (
        sentry.traces_sampler({"transaction_context": {"name": "GET /wallets"}}) == 0.25
    )


def test_init_sentry_uses_app_environment_as_fallback(monkeypatch):
    captured = {}
    monkeypatch.setattr(sentry.settings.sentry, "dsn", "https://public@example.com/1")
    monkeypatch.setattr(sentry.settings.sentry, "environment", None)
    monkeypatch.setattr(sentry.settings, "APP_ENV", "staging")
    monkeypatch.setattr(
        sentry.sentry_sdk, "init", lambda **kwargs: captured.update(kwargs)
    )

    sentry.init_sentry()

    assert captured["environment"] == "staging"
    assert captured["release"] == sentry.settings.sentry.release
    assert captured["traces_sampler"] is sentry.traces_sampler
    assert captured["before_send_transaction"] is sentry.before_send_transaction
    assert {"SqlalchemyIntegration", "RedisIntegration", "CeleryIntegration"} <= {
        integration.__class__.__name__ for integration in captured["integrations"]
    }


def test_init_sentry_returns_when_dsn_is_missing(monkeypatch):
    init_calls = []
    monkeypatch.setattr(sentry.settings.sentry, "dsn", None)
    monkeypatch.setattr(
        sentry.sentry_sdk, "init", lambda **kwargs: init_calls.append(kwargs)
    )

    sentry.init_sentry()

    assert init_calls == []


def test_empty_sentry_dsn_disables_sentry(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "")

    settings = SentrySettings()

    assert settings.dsn is None


def test_sentry_sensitive_keys_can_be_extended_from_env(monkeypatch):
    monkeypatch.setenv("SENTRY_EXTRA_SENSITIVE_KEYS", "credential, private-key")

    settings = SentrySettings()

    assert {"credential", "private-key"} <= settings.extra_sensitive_keys
    assert {"credential", "private-key"} <= settings.all_sensitive_keys


def test_request_id_is_returned_and_preserved(client):
    generated = client.get("/health")
    preserved = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert generated.headers["X-Request-ID"]
    assert preserved.headers["X-Request-ID"] == "request-123"


def test_sentry_middleware_uses_request_id_context(client, monkeypatch):
    contexts = {}
    monkeypatch.setattr(middleware.sentry_sdk, "set_context", contexts.__setitem__)
    monkeypatch.setattr(middleware.sentry_sdk, "set_tag", lambda *args: None)

    client.get("/health", headers={"X-Request-ID": "request-123"})

    assert contexts["request"]["request_id"] == "request-123"


def test_sentry_user_context_is_read_from_request_state():
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=7)))

    assert _sentry_user_from_request_state(request) == {"id": "7"}


def test_set_transfer_context_uses_fingerprint_and_user(monkeypatch):
    contexts = {}
    users = []
    monkeypatch.setattr(sentry.sentry_sdk, "set_context", contexts.__setitem__)
    monkeypatch.setattr(sentry.sentry_sdk, "set_user", users.append)

    sentry.set_transfer_context(
        transfer_id=42,
        user_id=7,
        idempotency_key="raw-secret-key",
    )

    assert contexts["transfer"] == {"transfer_id": 42, "user_id": 7}
    assert contexts["idempotency"] == {
        "key_fingerprint": idempotency_key_fingerprint("raw-secret-key")
    }
    assert "raw-secret-key" not in str(contexts)
    assert users == [{"id": "7"}]


def test_idempotent_transfer_passes_fingerprint_to_transfer(monkeypatch):
    class IdempotencyManager:
        def reserve(self, key, request_hash):
            return nullcontext()

    captured = {}

    def fake_create_transfer(*args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        transfers_service,
        "get_idempotency_manager",
        lambda: IdempotencyManager(),
    )
    monkeypatch.setattr(transfers_service, "create_transfer", fake_create_transfer)

    transfers_service.create_transfer_idempotent(
        object(),
        1,
        2,
        10,
        "raw-secret-key",
    )

    assert captured["idempotency_fingerprint"] == idempotency_key_fingerprint(
        "raw-secret-key"
    )


def test_transfer_propagates_business_context_to_celery(
    db,
    seeded_wallets,
    monkeypatch,
):
    from_wallet, to_wallet = seeded_wallets
    from_wallet_id = from_wallet.id
    to_wallet_id = to_wallet.id
    user_id = from_wallet.user_id
    db.rollback()

    task_calls = []
    monkeypatch.setattr(
        transfers_service.send_transaction_notification,
        "delay",
        lambda *args: task_calls.append(args),
    )

    token = request_id_ctx.set("request-1")
    try:
        transfer = transfers_service.create_transfer(
            db,
            from_wallet_id,
            to_wallet_id,
            Decimal("10.00"),
            idempotency_fingerprint="fingerprint-1",
        )
    finally:
        request_id_ctx.reset(token)

    assert task_calls == [
        (transfer.id, "request-1", user_id, "fingerprint-1"),
    ]


def test_celery_signal_sets_full_business_context(monkeypatch):
    contexts = {}
    tags = {}
    transfer_contexts = []

    def task_run(
        transfer_id,
        request_id=None,
        user_id=None,
        idempotency_fingerprint=None,
    ):
        return None

    task = SimpleNamespace(
        name="app.tasks.notifications.send_transaction_notification",
        request=SimpleNamespace(id="task-1", retries=2),
        run=task_run,
    )

    monkeypatch.setattr(celery_app.sentry_sdk, "set_context", contexts.__setitem__)
    monkeypatch.setattr(celery_app.sentry_sdk, "set_tag", tags.__setitem__)
    monkeypatch.setattr(
        celery_app,
        "set_transfer_context",
        lambda **kwargs: transfer_contexts.append(kwargs),
    )

    celery_app.set_sentry_task_context(
        task,
        "task-1",
        (42, "request-1", 7, "fingerprint-1"),
        {},
    )

    assert tags["component"] == "celery"
    assert tags["task_name"] == "app.tasks.notifications.send_transaction_notification"
    assert contexts["celery_task"] == {
        "request_id": "request-1",
        "transfer_id": 42,
        "task_id": "task-1",
        "retries": 2,
    }
    assert transfer_contexts == [
        {
            "transfer_id": 42,
            "user_id": 7,
            "idempotency_fingerprint": "fingerprint-1",
        }
    ]


def test_celery_task_is_free_of_sentry(monkeypatch):
    monkeypatch.setattr(notifications.random, "random", lambda: 1.0)

    notifications.send_transaction_notification.run(
        42,
        "request-1",
        7,
        "fingerprint-1",
    )
