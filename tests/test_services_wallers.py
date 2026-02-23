from app.services.exceptions import NotFound
from app.services.wallets import get_wallet


def test_get_wallet_by_id_not_found(db):
    try:
        get_wallet(db, wallet_id=999999)
        raise AssertionError("Expected NotFound")
    except NotFound:
        pass
