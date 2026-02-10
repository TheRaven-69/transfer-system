from decimal import Decimal
from app.services.wallets import create_wallet_with_autouser, get_wallet
from app.services.exceptions import NotFound
from app.db.models import Wallet

def test_create_wallet_with_autouser_returns_wallet_with_user(db):
    w = create_wallet_with_autouser(db)

    assert isinstance(w, Wallet)
    assert w.id is not None
    assert w.user_id is not None
    assert w.balance == Decimal("100.00") 
    assert w.user is not None
    assert w.user.id == w.user_id

def test_get_wallet_by_id_not_found(db):
    try:
        get_wallet(db, 999999)
        assert False, "Expected NotFound"
    except NotFound:
        assert True
