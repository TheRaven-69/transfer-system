import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.metrics import DB_QUERY_DURATION_SECONDS, DB_QUERY_ERRORS_TOTAL
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


@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_started_at = time.perf_counter()
    context._query_operation = _query_operation(statement)


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    started_at = getattr(context, "_query_started_at", None)
    if started_at is None:
        return

    operation = getattr(context, "_query_operation", "other")
    DB_QUERY_DURATION_SECONDS.labels(operation=operation).observe(
        time.perf_counter() - started_at
    )


@event.listens_for(engine, "handle_error")
def handle_query_error(exception_context):
    context = exception_context.execution_context
    operation = getattr(context, "_query_operation", "other") if context else "other"
    DB_QUERY_ERRORS_TOTAL.labels(operation=operation).inc()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
