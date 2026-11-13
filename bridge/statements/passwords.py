from core.crypto import decrypt, encrypt

from .models import StatementPassword


def save(key, label, password):
    StatementPassword.objects.update_or_create(key=key, label=label, defaults={"password_encrypted": encrypt(password)})


def candidates(key):
    """Decrypted passwords for a bank, in memory only. Never log or return them to a caller outside this app."""
    return [decrypt(p.password_encrypted) for p in StatementPassword.objects.filter(key=key).order_by("created_at")]
