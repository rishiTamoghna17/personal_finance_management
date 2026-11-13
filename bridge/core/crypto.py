"""Encryption for secrets kept in the database (Gmail tokens, statement passwords).
The key lives only in .env (BRIDGE_ENCRYPTION_KEY), never in the database."""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CryptoError(Exception):
    pass


def _fernet():
    key = settings.BRIDGE_ENCRYPTION_KEY
    if not key:
        raise CryptoError("BRIDGE_ENCRYPTION_KEY is not set in .env")
    return Fernet(key.encode())


def encrypt(text):
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise CryptoError("cannot decrypt: wrong BRIDGE_ENCRYPTION_KEY or damaged value") from None
