import os
from datetime import timedelta

os.environ.setdefault("ENV_FILE", ".env.test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.celery_app import celery_app
from app.core.security import create_token
from app.db.models import Base, User, Wallet
from app.db.session import get_db
from app.main import app
from tests.factories import make_user


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
def auth_user(db):
    user = User(
        username="authenticated_user",
        email="authenticated@example.com",
        password_hash="disabled",
    )
    db.add(user)
    db.flush()
    wallet = Wallet(user_id=user.id, balance=1000)
    db.add(wallet)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers_factory():
    def factory(user_id: int) -> dict[str, str]:
        token, _ = create_token(user_id, "access", timedelta(minutes=5))
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture()
def auth_headers(auth_user, auth_headers_factory):
    return auth_headers_factory(auth_user.id)


@pytest.fixture()
def seeded_wallets(db):
    u1 = make_user()
    u2 = make_user()
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
