from decimal import Decimal
import pytest

from app.services.users import create_user, get_user_by_id, create_wallet_for_user
from app.services.exceptions import NotFound
from app.db.models import User, Wallet

def test_create_user(db):
    u = create_user(db)
    assert isinstance(u, User)
    assert u.id is not None

def test_get_user_by_id_success(db):
    u = create_user(db)
    u2 = get_user_by_id(db, u.id)
    assert u2.id == u.id

def test_get_user_by_id_not_found(db):
    with pytest.raises(NotFound):
        get_user_by_id(db, 999999)

def test_create_wallet_for_user(db):
    u = create_user(db)
    w = create_wallet_for_user(db, u.id)

    assert isinstance(w, Wallet)
    assert w.user_id == u.id
    assert w.balance == Decimal("100.00")  
