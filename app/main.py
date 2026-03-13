import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.routes import router
from app.core.logging import setup_logging
from app.core.middlaware import RequestIDMiddleware
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="Transfer System API", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)

logger.info("Application module loaded")


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


@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/health")
def health():
    logger.info("Health endpoint called")
    return {"status": "ok"}
