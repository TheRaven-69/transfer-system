from app.db.models import Wallet


def create_wallet_with_autouser():
    pass


def get_wallet_by_id():
    pass
# TODO: validate initial_balance >= 0
# TODO: create wallet for existing user
# TODO: prevent wallet creation if user does not exist
# TODO: prevent multiple wallets per user (if constrained)
# TODO: auto-create user when creating wallet without user_id
# TODO: return created user + wallet
# TODO: fetch wallet by id
# TODO: raise ServiceError on all invalid states
