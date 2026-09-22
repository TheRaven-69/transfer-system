from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenDecodeError, decode_token
from app.db.models import User
from app.db.session import get_db
from app.services.exceptions import AuthenticationRequired, InvalidToken

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    email: str


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationRequired()
    try:
        payload = decode_token(credentials.credentials, "access")
    except TokenDecodeError as exc:
        raise InvalidToken() from exc

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise InvalidToken()
    principal = AuthenticatedUser(
        id=user.id,
        username=user.username,
        email=user.email,
    )
    # End the read-only autobegin transaction so write use cases can own their
    # top-level transaction and commit atomically.
    db.rollback()
    request.state.user = principal
    return principal
