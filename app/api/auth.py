from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.settings import settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth import (
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.exceptions import AuthenticationRequired

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.auth.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.APP_ENV in {"staging", "production"},
        samesite="lax",
        path="/auth",
    )


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.auth.access_token_minutes * 60,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, payload.username, payload.email, payload.password)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
        "wallet": {
            "id": user.wallet.id,
            "balance": user.wallet.balance,
        },
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    access_token, refresh_token = login_user(db, payload.identifier, payload.password)
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if refresh_token is None:
        raise AuthenticationRequired()
    access_token, new_refresh_token = rotate_refresh_token(db, refresh_token)
    _set_refresh_cookie(response, new_refresh_token)
    return _token_response(access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if refresh_token is not None:
        revoke_refresh_token(db, refresh_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")


@router.get("/me")
def me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, current_user.id)
    if user is None:
        raise AuthenticationRequired()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
        "wallet": {
            "id": user.wallet.id,
            "balance": user.wallet.balance,
        },
    }
