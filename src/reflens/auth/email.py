"""Email verification sending."""

import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from reflens.config import Settings

logger = logging.getLogger(__name__)


def _get_mail_config(settings: Settings) -> ConnectionConfig | None:
    if not settings.mail_server or not settings.mail_from:
        return None
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=bool(settings.mail_username),
    )


async def send_verification_email(
    email: str, token: str, settings: Settings
) -> bool:
    """Send a verification email. Returns False if mail is not configured."""
    config = _get_mail_config(settings)
    if config is None:
        logger.warning(
            "Email not configured. Verification link: %s/verify-email?token=%s",
            settings.frontend_url,
            token,
        )
        return False

    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""\
    <h2>Welcome to RefLens</h2>
    <p>Click the link below to verify your email address:</p>
    <p><a href="{verify_url}">Verify my email</a></p>
    <p>This link expires in 24 hours.</p>
    <p>If you didn't create an account, you can ignore this email.</p>
    """

    message = MessageSchema(
        subject="RefLens - Verify your email",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )

    fm = FastMail(config)
    await fm.send_message(message)
    return True
