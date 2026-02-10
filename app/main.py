from fastapi import FastAPI
from app.api.routes import router
from app.db.session import engine
from app.db.models import Base
from app.services.exceptions import BadRequest, NotFound, Conflict
from fastapi.responses import JSONResponse

app = FastAPI(title="Transfer System API")


@app.exception_handler(BadRequest)
async def handle_bad_request(request, exc: BadRequest):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(NotFound)
async def handle_not_found(request, exc: NotFound):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(Conflict)
async def handle_conflict(request, exc: Conflict):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)},
    )


Base.metadata.create_all(bind=engine)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok"}



