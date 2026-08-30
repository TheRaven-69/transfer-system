from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    TokenDecodeError,
    create_token,
    decode_token,
    hash_password,
    token_hash,
    verify_password,
)
from app.core.settings import settings
from app.db.models import RefreshToken, User
from app.db.tx import transaction_scope
from app.services.exceptions import (
    EmailAlreadyExists,
    InvalidCredentials,
    InvalidToken,
    UsernameAlreadyExists,
)
from app.services.wallets import create_wallet_for_user

_DUMMY_PASSWORD_HASH = hash_password("invalid-password-placeholder")


def register_user(db: Session, username: str, email: str, password: str) -> User:
    try:
        with transaction_scope(db):
            if db.scalar(select(User.id).where(User.username == username)) is not None:
                raise UsernameAlreadyExists()
            if db.scalar(select(User.id).where(User.email == email)) is not None:
                raise EmailAlreadyExists()

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
            user.wallet = create_wallet_for_user(db, user.id)
    except IntegrityError as exc:
        constraint = str(exc.orig).casefold()
        if "username" in constraint:
            raise UsernameAlreadyExists() from exc
        if "email" in constraint:
            raise EmailAlreadyExists() from exc
        raise
    return user


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    return db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )


def _create_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token, _ = create_token(
        user.id,
        "access",
        timedelta(minutes=settings.auth.access_token_minutes),
    )
    refresh_token, refresh_expires_at = create_token(
        user.id,
        "refresh",
        timedelta(days=settings.auth.refresh_token_days),
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash(refresh_token),
            expires_at=refresh_expires_at,
        )
    )
    return access_token, refresh_token


def login_user(db: Session, identifier: str, password: str) -> tuple[str, str]:
    with transaction_scope(db):
        user = _find_user_by_identifier(db, identifier)
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        if not verify_password(password, password_hash) or user is None:
            raise InvalidCredentials()
        return _create_token_pair(db, user)


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(raw_token, "refresh")
    except TokenDecodeError as exc:
        raise InvalidToken() from exc

    now = datetime.now(timezone.utc)
    with transaction_scope(db):
        user_id = db.scalar(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash(raw_token),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
                RefreshToken.user_id == int(payload["sub"]),
            )
            .values(revoked_at=now)
            .returning(RefreshToken.user_id)
        )
        if user_id is None:
            raise InvalidToken()

        user = db.get(User, user_id)
        if user is None:
            raise InvalidToken()
        return _create_token_pair(db, user)


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    try:
        decode_token(raw_token, "refresh")
    except TokenDecodeError:
        return

    with transaction_scope(db):
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash(raw_token),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
