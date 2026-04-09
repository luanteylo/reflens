"""Authentication endpoints: signup, login, logout, refresh, verify."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from reflens.auth.service import (
    AuthError,
    change_password,
    delete_account,
    login,
    refresh_tokens,
    signup,
    verify_email,
)
from reflens.config import get_settings
from reflens.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class DeleteAccountRequest(BaseModel):
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    plan: str
    email_verified: bool
    created_at: str | None = None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    secure = not settings.frontend_url.startswith("http://localhost")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )


@router.post("/signup", response_model=AuthResponse)
async def signup_endpoint(body: SignupRequest):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Auth is not enabled")

    session = get_session()
    try:
        await signup(body.email, body.password, session, settings)
        return AuthResponse(message="Account created. Check your email for verification.")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


@router.post("/login", response_model=UserResponse)
def login_endpoint(body: LoginRequest, response: Response):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Auth is not enabled")

    session = get_session()
    try:
        access_token, refresh_token, user = login(
            body.email, body.password, session, settings
        )
        _set_auth_cookies(response, access_token, refresh_token)
        return UserResponse(
            user_id=user.id,
            email=user.email,
            plan=user.plan,
            email_verified=user.email_verified,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


@router.post("/logout", response_model=AuthResponse)
def logout_endpoint(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return AuthResponse(message="Logged out")


@router.post("/refresh", response_model=AuthResponse)
def refresh_endpoint(request: Request, response: Response):
    settings = get_settings()
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    session = get_session()
    try:
        access_token, new_refresh = refresh_tokens(token, session, settings)
        _set_auth_cookies(response, access_token, new_refresh)
        return AuthResponse(message="Tokens refreshed")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


@router.post("/verify-email", response_model=AuthResponse)
def verify_email_endpoint(body: VerifyRequest):
    settings = get_settings()
    session = get_session()
    try:
        verify_email(body.token, session, settings)
        return AuthResponse(message="Email verified. You can now log in.")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


def _get_current_user_id(request: Request) -> str:
    """Extract user_id from access token cookie."""
    settings = get_settings()
    from reflens.auth.security import decode_token

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token, settings)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/change-password", response_model=AuthResponse)
def change_password_endpoint(body: ChangePasswordRequest, request: Request):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Auth is not enabled")

    user_id = _get_current_user_id(request)
    session = get_session()
    try:
        change_password(user_id, body.current_password, body.new_password, session)
        return AuthResponse(message="Password changed successfully")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


@router.delete("/account", response_model=AuthResponse)
def delete_account_endpoint(body: DeleteAccountRequest, request: Request, response: Response):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Auth is not enabled")

    user_id = _get_current_user_id(request)
    session = get_session()
    try:
        delete_account(user_id, body.password, session)
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
        return AuthResponse(message="Account deleted")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        session.close()


@router.get("/me", response_model=UserResponse)
def me_endpoint(request: Request):
    settings = get_settings()
    if not settings.auth_enabled:
        return UserResponse(
            user_id="local", email="local@localhost", plan="free", email_verified=True
        )

    user_id = _get_current_user_id(request)
    session = get_session()
    try:
        from sqlalchemy import select
        from reflens.db.models import User

        user = session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return UserResponse(
            user_id=user.id,
            email=user.email,
            plan=user.plan,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
    finally:
        session.close()
