from django.db import models


class StatementPassword(models.Model):
    """A statement password, encrypted with BRIDGE_ENCRYPTION_KEY. Entered only through a hidden prompt.
    A bank may have several (e.g. one per card); each is tried in turn."""

    key = models.SlugField(max_length=32, db_index=True)  # hsbc, icici, axis, sbi-card, hdfc
    label = models.CharField(max_length=64)  # owner's note, e.g. "Amex card"; never the password
    password_encrypted = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "label"], name="statement_password_key_label")]

    def __str__(self):
        return f"{self.key}/{self.label}"
