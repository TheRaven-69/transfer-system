from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.db.models import Base
from app.db.session import engine
from app.services.exceptions import (
    BadRequest,
    Conflict,
    InsufficientFunds,
    NotFound,
)

app = FastAPI(title="Transfer System API")


def _error_response(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
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


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
