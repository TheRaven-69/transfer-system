import uuid

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.request_context import request_id_ctx


def _sentry_user_from_request_state(request: Request) -> dict[str, str] | None:
    user = getattr(request.state, "user", None)
    if user is None:
        return None

    user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    if user_id is None:
        return None

    return {"id": str(user_id)}


class SentryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        token = request_id_ctx.set(request_id)
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

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
