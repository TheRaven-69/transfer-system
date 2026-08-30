import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import jwt

from app.core.settings import settings

TokenType = Literal["access", "refresh"]
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LENGTH = 64


class TokenDecodeError(ValueError):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LENGTH,
    )
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived_key).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_key = encoded_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_key),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual_key, expected_key)


def create_token(
    user_id: int, token_type: TokenType, lifetime: timedelta
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + lifetime
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": uuid4().hex,
        "iat": now,
        "exp": expires_at,
        "iss": settings.auth.issuer,
    }
    token = jwt.encode(payload, settings.auth.jwt_secret, algorithm="HS256")
    return token, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.auth.issuer,
            options={"require": ["sub", "type", "jti", "iat", "exp", "iss"]},
        )
        if payload.get("type") != expected_type:
            raise TokenDecodeError("Unexpected token type")
        int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenDecodeError("Invalid token") from exc
    return payload


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
