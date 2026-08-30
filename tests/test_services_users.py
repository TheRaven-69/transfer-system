import pytest

from app.db.models import Wallet
from app.services.exceptions import NotFound
from app.services.users import get_user_by_id
from tests.factories import make_user


def test_get_user_by_id_success(db):
    u = make_user()
    db.add(u)
    db.flush()
    db.add(Wallet(user_id=u.id))
    db.commit()

    u2 = get_user_by_id(db, u.id)
    assert u2.id == u.id
    assert u2.wallet is not None
    assert u2.wallet.id is not None


def test_get_user_by_id_not_found(db):
    with pytest.raises(NotFound):
        get_user_by_id(db, 999999)
