import logging
import time
import uuid

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics.collectors import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUEST_OUTCOMES_TOTAL,
    HTTP_REQUESTS_TOTAL,
)
from app.core.request_context import request_id_ctx

logger = logging.getLogger(__name__)


def _sentry_user_from_request_state(request: Request) -> dict[str, str] | None:
    user = getattr(request.state, "user", None)
    if user is None:
        return None

    user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    if user_id is None:
        return None

    return {"id": str(user_id)}


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "http_request_completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": round(duration_ms, 3),
                    }
                },
            )


class SentryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request_id_ctx.get("-")
        sentry_sdk.set_tag("component", "api")
        sentry_sdk.set_context(
            "request",
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        user_context = _sentry_user_from_request_state(request)
        if user_context is not None:
            sentry_sdk.set_user(user_context)

        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        method = request.method
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start_time
            route = request.scope.get("route")
            path = route.path if route and hasattr(route, "path") else "__unmatched__"
            if status_code < 400:
                outcome = "successful"
            elif status_code < 500:
                outcome = "client_error"
            else:
                outcome = "server_error"

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path=path,
                status=str(status_code),
            ).inc()

            HTTP_REQUEST_OUTCOMES_TOTAL.labels(
                method=method,
                path=path,
                outcome=outcome,
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                path=path,
            ).observe(duration)
