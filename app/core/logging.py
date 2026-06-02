import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import request_id_ctx
from app.core.settings import settings


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            log_data.update(extra_fields)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.addFilter(RequestIDFilter())
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
