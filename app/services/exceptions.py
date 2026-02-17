class ServiceError(Exception):
    """Base class for exceptions in this service."""

    def __str__(self) -> str:
        return self.message


class BadRequest(ServiceError):
    """Invalid inpud data."""
    pass


class NotFound(ServiceError):
    """Requested entity was not found."""


class Conflict(ServiceError):
    """Operation cannot be completed due to current state of the resource."""
    pass


class UserNotFound(NotFound):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    @property
    def message(self) -> str:
        return f"User with id {self.user_id} not found."


class WalletNotFound(NotFound):
    def __init__(self, wallet_id: int) -> None:
        self.wallet_id = wallet_id

    @property
    def message(self) -> str:
        return f"Wallet with id {self.wallet_id} not found."


class UserWalletNotFound(NotFound):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    @property
    def message(self) -> str:
        return f"Wallet for user with id {self.user_id} not found."


class CannotTransferToSameWallet(BadRequest):
    message = "Cannot transfer to the same wallet"


class TransferAmountRequired(BadRequest):
    message = "Amount is required"


class InvalidTransferAmount(BadRequest):
    message = "Amount must be greater than zero"


class InsufficientFunds(Conflict):
    message = "Insufficient funds"


class CacheUnavailable(ServiceError):
    message = "Cache service is unavailable"
