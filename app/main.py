from fastapi import FastAPI, Depends
from app.api.routes import router
from app.db.session import engine
from app.models import Base

app = FastAPI(title="Transfer System API")

Base.metadata.create_all(bind=engine)

app.include_router(router)

@app.get("/")
def root():
    return {"status": "ok"}



