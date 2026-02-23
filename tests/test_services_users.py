import pytest

from app.db.models import User
from app.services.exceptions import NotFound
from app.services.users import create_user, get_user_by_id


def test_create_user(db):
    u = create_user(db)
    assert isinstance(u, User)
    assert u.id is not None
    assert u.wallet is not None
    assert u.wallet.user_id == u.id


def test_get_user_by_id_success(db):
    u = create_user(db)
    u2 = get_user_by_id(db, u.id)
    assert u2.id == u.id
    assert u2.wallet is not None
    assert u2.wallet.id is not None


def test_get_user_by_id_not_found(db):
    with pytest.raises(NotFound):
        get_user_by_id(db, 999999)
