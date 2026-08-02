import logging

import pytest

import app.services.users as users_service
from app.db.models import User
from app.services.exceptions import NotFound
from app.services.users import create_user, get_user_by_id


def test_create_user(db):
    u = create_user(db)
    assert isinstance(u, User)
    assert u.id is not None
    assert u.wallet is not None
    assert u.wallet.user_id == u.id


def test_create_user_logs_only_after_successful_commit(db, caplog):
    with caplog.at_level(logging.INFO):
        user = create_user(db)

    events = [record.message for record in caplog.records]
    assert events.count("wallet_created") == 1
    assert events.count("user_created") == 1
    assert user.id is not None


def test_create_user_does_not_log_success_after_rollback(db, monkeypatch, caplog):
    original_create_wallet = users_service.create_wallet_for_user

    def create_wallet_then_fail(session, user_id):
        original_create_wallet(session, user_id)
        raise RuntimeError("force rollback")

    monkeypatch.setattr(
        users_service,
        "create_wallet_for_user",
        create_wallet_then_fail,
    )

    with (
        caplog.at_level(logging.INFO),
        pytest.raises(RuntimeError, match="force rollback"),
    ):
        create_user(db)

    events = [record.message for record in caplog.records]
    assert "wallet_created" not in events
    assert "user_created" not in events


def test_get_user_by_id_success(db):
    u = create_user(db)
    u2 = get_user_by_id(db, u.id)
    assert u2.id == u.id
    assert u2.wallet is not None
    assert u2.wallet.id is not None


def test_get_user_by_id_not_found(db):
    with pytest.raises(NotFound):
        get_user_by_id(db, 999999)
