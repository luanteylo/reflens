"""Simple key encryption using the app's secret key."""

import base64
import hashlib

from cryptography.fernet import Fernet

from reflens.config import Settings


def _get_fernet(settings: Settings) -> Fernet:
    # Derive a 32-byte key from the secret
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_key(api_key: str, settings: Settings) -> str:
    f = _get_fernet(settings)
    return f.encrypt(api_key.encode()).decode()


def decrypt_key(encrypted: str, settings: Settings) -> str:
    f = _get_fernet(settings)
    return f.decrypt(encrypted.encode()).decode()
