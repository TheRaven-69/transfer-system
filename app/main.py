from fastapi import FastAPI, Depends
from app.api.routes import router
from app.db.session import engine
from app.db.models import Base

app = FastAPI(title="Transfer System API")

# TODO: create database tables on startup
Base.metadata.create_all(bind=engine)

# TODO: include API router
app.include_router(router)

# TODO: register global ServiceError exception handler
@app.get("/")
def root():
    return {"status": "ok"}



