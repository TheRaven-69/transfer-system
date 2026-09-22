import logging

import pytest

import app.services.auth as auth_service
from app.db.models import User
from app.services.auth import register_user
from app.services.exceptions import NotFound
from app.services.users import get_user_by_id


def _register_user(db, username: str = "service-user") -> User:
    return register_user(
        db,
        username,
        f"{username}@example.com",
        "correct-horse-battery-staple",
    )


def test_register_user_creates_wallet(db):
    user = _register_user(db)

    assert user.id is not None
    assert user.wallet is not None
    assert user.wallet.user_id == user.id


def test_register_user_logs_only_after_successful_commit(db, caplog):
    with caplog.at_level(logging.INFO):
        user = _register_user(db)

    events = [record.message for record in caplog.records]
    assert events.count("wallet_created") == 1
    assert events.count("user_created") == 1
    assert user.id is not None


def test_register_user_does_not_log_success_after_rollback(db, monkeypatch, caplog):
    original_create_wallet = auth_service.create_wallet_for_user

    def create_wallet_then_fail(session, user_id):
        original_create_wallet(session, user_id)
        raise RuntimeError("force rollback")

    monkeypatch.setattr(
        auth_service,
        "create_wallet_for_user",
        create_wallet_then_fail,
    )

    with (
        caplog.at_level(logging.INFO),
        pytest.raises(RuntimeError, match="force rollback"),
    ):
        _register_user(db)

    events = [record.message for record in caplog.records]
    assert "wallet_created" not in events
    assert "user_created" not in events


def test_get_user_by_id_success(db):
    user = _register_user(db)

    loaded_user = get_user_by_id(db, user.id)

    assert loaded_user.id == user.id
    assert loaded_user.wallet is not None
    assert loaded_user.wallet.id is not None


def test_get_user_by_id_not_found(db):
    with pytest.raises(NotFound):
        get_user_by_id(db, 999999)
