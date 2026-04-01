import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.core.logging import setup_logging
from app.core.metrics import HTTP_EXCEPTIONS_TOTAL
from app.core.middleware import MetricsMiddleware, RequestIDMiddleware
from app.core.sentry import init_sentry
from app.db.models import Base
from app.db.session import engine
from app.services.exceptions import (
    BadRequest,
    Conflict,
    NotFound,
    ServiceError,
)

setup_logging()
init_sentry()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="Transfer System API", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _request_path(request: Request) -> str:
    route = request.scope.get("route")
    return route.path if route and hasattr(route, "path") else request.url.path


def _track_exception(request: Request, status_code: int, exc: Exception) -> None:
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method,
        path=_request_path(request),
        status=str(status_code),
        exception_type=type(exc).__name__,
    ).inc()


def _error_response(
    request: Request, status_code: int, exc: Exception, detail: str | None = None
) -> JSONResponse:
    _track_exception(request, status_code, exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail or str(exc)},
    )


def _service_error_status(exc: ServiceError) -> int:
    if isinstance(exc, BadRequest):
        return 400
    if isinstance(exc, NotFound):
        return 404
    if isinstance(exc, Conflict):
        return 409
    return 500


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception occurred: path=%s method=%s",
        _request_path(request),
        request.method,
    )
    return _error_response(request, 500, exc, detail="Internal server error")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(request, 422, exc, detail="Validation error")


@app.exception_handler(ServiceError)
async def service_exception_handler(request: Request, exc: ServiceError):
    return _error_response(request, _service_error_status(exc), exc)


Base.metadata.create_all(bind=engine)

app.include_router(router)


def _static_page(filename: str) -> FileResponse:
    return FileResponse(STATIC_DIR / filename)


@app.get("/", response_class=FileResponse)
def root():
    return _static_page("index.html")


@app.get("/ui/users", response_class=FileResponse)
def users_frontend():
    return _static_page("users.html")


@app.get("/ui/wallets", response_class=FileResponse)
def wallets_frontend():
    return _static_page("wallets.html")


@app.get("/ui/transfers", response_class=FileResponse)
def transfers_frontend():
    return _static_page("transfers.html")


@app.get("/metrics")
def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
