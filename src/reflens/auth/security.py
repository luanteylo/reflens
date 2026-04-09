"""JWT token creation/verification and password hashing."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from reflens.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_verification_token(user_id: str, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(hours=24)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "email_verify"},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, settings: Settings) -> dict:
    """Decode and verify a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
