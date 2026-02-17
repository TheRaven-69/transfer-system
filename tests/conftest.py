import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db
from app.db.models import Base, User, Wallet


@pytest.fixture()
def engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


@pytest.fixture()
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(engine, tables):
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_wallets(db):
    u1 = User()
    u2 = User()
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    w1 = Wallet(user_id=u1.id, balance=1000)
    w2 = Wallet(user_id=u2.id, balance=0)
    db.add_all([w1, w2])
    db.commit()
    db.refresh(w1)
    db.refresh(w2)

    return w1, w2
