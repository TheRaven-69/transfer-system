class ServiceError(Exception):
    """Base class for exceptions in this service."""
    pass


class BadRequest(ServiceError):
    """Invalid inpud data."""
    pass


class NotFound(ServiceError):
    """Requested entity was not found."""
    pass


class Conflict(ServiceError):
    """Operation cannot be completed due to current state of the resource."""
    pass


