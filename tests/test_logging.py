import json
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal

from app.core.celery_app import celery_app
from app.core.logging import JsonFormatter, RequestIDFilter
from app.core.request_context import request_id_ctx


def _record(message: str = "test_event") -> logging.LogRecord:
    return logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_json_formatter_includes_request_id_and_extra_fields():
    token = request_id_ctx.set("request-123")
    try:
        record = _record()
        record.extra_fields = {"transfer_id": 42}
        RequestIDFilter().filter(record)

        payload = json.loads(JsonFormatter().format(record))

        assert payload["message"] == "test_event"
        assert payload["request_id"] == "request-123"
        assert payload["transfer_id"] == 42
    finally:
        request_id_ctx.reset(token)


def test_json_formatter_preserves_reserved_fields():
    record = _record()
    record.request_id = "trusted-request"
    record.extra_fields = {
        "message": "overridden",
        "request_id": "spoofed-request",
        "level": "OVERRIDDEN",
    }

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "test_event"
    assert payload["request_id"] == "trusted-request"
    assert payload["level"] == "INFO"


def test_json_formatter_stringifies_non_serializable_extra_fields():
    class ExampleModel:
        def __str__(self) -> str:
            return "ExampleModel(id=7)"

    record = _record()
    record.extra_fields = {
        "amount": Decimal("10.25"),
        "created_at": datetime(2026, 7, 31, 12, 30, tzinfo=timezone.utc),
        "model": ExampleModel(),
    }

    payload = json.loads(JsonFormatter().format(record))

    assert payload["amount"] == "10.25"
    assert payload["created_at"] == "2026-07-31 12:30:00+00:00"
    assert payload["model"] == "ExampleModel(id=7)"


def test_json_formatter_includes_concrete_exception_details():
    record = _record("operation_failed")
    try:
        raise ValueError("invalid value")
    except ValueError:
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert payload["error_type"] == "ValueError"
    assert payload["error_message"] == "invalid value"
    assert "ValueError: invalid value" in payload["exception"]


def test_celery_preserves_root_logger_configuration():
    assert celery_app.conf.worker_hijack_root_logger is False


def test_http_request_log_contains_access_fields(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = client.get(
            "/health?source=test",
            headers={"X-Request-ID": "request-123"},
        )

    record = next(
        record
        for record in caplog.records
        if record.message == "http_request_completed"
    )

    assert response.status_code == 200
    assert record.request_id == "request-123"
    assert record.extra_fields["method"] == "GET"
    assert record.extra_fields["path"] == "/health"
    assert record.extra_fields["status"] == 200
    assert isinstance(record.extra_fields["duration_ms"], float)
    assert record.extra_fields["duration_ms"] >= 0


def test_http_request_log_records_error_status(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = client.get("/missing")

    record = next(
        record
        for record in caplog.records
        if record.message == "http_request_completed"
    )

    assert response.status_code == 404
    assert record.extra_fields["path"] == "/missing"
    assert record.extra_fields["status"] == 404
