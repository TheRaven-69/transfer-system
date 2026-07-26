from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings

engine_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _query_operation(statement: str) -> str:
    parts = statement.lstrip().split(maxsplit=1)
    if not parts:
        return "other"

    operation = parts[0].lower()
    if operation in {"select", "insert", "update", "delete"}:
        return operation
    return "other"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
