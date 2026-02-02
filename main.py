from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from models import Base
from database import engine, get_db

app = FastAPI(title="Transfer System API")
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "ok"}


