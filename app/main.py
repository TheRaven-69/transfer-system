import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.core.logging import setup_logging
from app.core.middleware import MetricsMiddleware, RequestIDMiddleware
from app.db.models import Base
from app.db.session import engine
from app.services.exceptions import (
    BadRequest,
    Conflict,
    InsufficientFunds,
    NotFound,
)

setup_logging()
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


def _error_response(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception occurred: path=%s method=%s",
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(InsufficientFunds)
async def handle_insufficient_funds(request: Request, exc: Conflict):
    return _error_response(409, exc)


@app.exception_handler(BadRequest)
async def handle_bad_request(request: Request, exc: BadRequest):
    return _error_response(400, exc)


@app.exception_handler(NotFound)
async def handle_not_found(request: Request, exc: NotFound):
    return _error_response(404, exc)


@app.exception_handler(Conflict)
async def handle_conflict(request: Request, exc: Conflict):
    return _error_response(409, exc)


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
