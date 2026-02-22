import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.celery_app import celery_app
from app.db.models import Base, User, Wallet
from app.db.session import get_db
from app.main import app

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("NOTIFY_DELAY_SEC", "0")


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        value = self.data.get(key)
        if isinstance(value, str):
            return value.encode("utf-8")
        return value

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def delete(self, key):
        self.data.pop(key, None)
        return 1


celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)


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
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    session = session_local()
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

    return w1, w2


@pytest.fixture()
def fake_redis():
    return FakeRedis()
