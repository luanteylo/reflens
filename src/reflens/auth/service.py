"""Auth business logic: signup, login, verify, refresh."""

import logging
import re

from sqlalchemy.orm import Session

from reflens.auth.email import send_verification_email
from reflens.auth.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    hash_password,
    verify_password,
)
from reflens.config import Settings
from reflens.db.models import User

logger = logging.getLogger(__name__)

PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _get_user_by_email(session: Session, email: str) -> User | None:
    from sqlalchemy import select

    return session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()


def _get_user_by_id(session: Session, user_id: str) -> User | None:
    from sqlalchemy import select

    return session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()


def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AuthError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not PASSWORD_PATTERN.match(password):
        raise AuthError("Password must contain at least one letter and one digit")


async def signup(
    email: str, password: str, session: Session, settings: Settings
) -> User:
    email = email.lower().strip()
    validate_password(password)

    existing = _get_user_by_email(session, email)
    if existing:
        raise AuthError("An account with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Send verification email (don't fail signup if email fails)
    token = create_verification_token(user.id, settings)
    try:
        await send_verification_email(email, token, settings)
    except Exception:
        logger.warning("Failed to send verification email to %s", email, exc_info=True)
        # In dev: log the link so the user can verify manually
        logger.info(
            "Verification link: %s/verify-email?token=%s",
            settings.frontend_url,
            token,
        )

    return user


def login(
    email: str, password: str, session: Session, settings: Settings
) -> tuple[str, str, User]:
    """Returns (access_token, refresh_token, user). Raises AuthError on failure."""
    email = email.lower().strip()
    user = _get_user_by_email(session, email)

    if user is None:
        # Dummy hash to prevent timing enumeration
        verify_password("dummy", hash_password("dummy"))
        raise AuthError("Invalid email or password", 401)

    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password", 401)

    if not user.email_verified:
        raise AuthError("Please verify your email before logging in", 403)

    if not user.is_active:
        raise AuthError("Account is deactivated", 403)

    access_token = create_access_token(user.id, settings)
    refresh_token = create_refresh_token(user.id, settings)
    return access_token, refresh_token, user


def verify_email(token: str, session: Session, settings: Settings) -> User:
    """Verify email from token. Returns the user."""
    try:
        payload = decode_token(token, settings)
    except Exception:
        raise AuthError("Invalid or expired verification link")

    if payload.get("type") != "email_verify":
        raise AuthError("Invalid verification link")

    user = _get_user_by_id(session, payload["sub"])
    if user is None:
        raise AuthError("User not found")

    if user.email_verified:
        return user  # Already verified

    user.email_verified = True
    session.commit()
    session.refresh(user)
    return user


def change_password(
    user_id: str,
    current_password: str,
    new_password: str,
    session: Session,
) -> None:
    """Change user password. Raises AuthError on failure."""
    validate_password(new_password)
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise AuthError("User not found", 404)
    if not verify_password(current_password, user.hashed_password):
        raise AuthError("Current password is incorrect", 401)
    user.hashed_password = hash_password(new_password)
    session.commit()


def delete_account(
    user_id: str, password: str, session: Session
) -> None:
    """Delete user account after password confirmation."""
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise AuthError("User not found", 404)
    if not verify_password(password, user.hashed_password):
        raise AuthError("Password is incorrect", 401)
    session.delete(user)
    session.commit()


def refresh_tokens(
    refresh_token_str: str, session: Session, settings: Settings
) -> tuple[str, str]:
    """Issue new token pair from a valid refresh token."""
    try:
        payload = decode_token(refresh_token_str, settings)
    except Exception:
        raise AuthError("Invalid or expired refresh token", 401)

    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type", 401)

    user = _get_user_by_id(session, payload["sub"])
    if user is None or not user.is_active:
        raise AuthError("User not found or deactivated", 401)

    access_token = create_access_token(user.id, settings)
    new_refresh = create_refresh_token(user.id, settings)
    return access_token, new_refresh
