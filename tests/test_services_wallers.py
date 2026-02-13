from app.services.wallets import get_wallet
from app.services.exceptions import NotFound


def test_get_wallet_by_id_not_found(db):
    try:
        get_wallet(db, 999999)
        assert False, "Expected NotFound"
    except NotFound:
        assert True
