"""A text field stored encrypted (Fernet, key BRIDGE_ENCRYPTION_KEY from .env). Used for bank SMS and email bodies,
so a copy of the database (or a backup) does not reveal message text without the key."""
from django.db import models

from .crypto import decrypt, encrypt

PREFIX = "enc1:"


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if value is None or not value.startswith(PREFIX):
            return value  # rows written before encryption; the migration re-saves them
        return decrypt(value[len(PREFIX):])

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value.startswith(PREFIX):
            return value
        return PREFIX + encrypt(value)
