from django.db import models


class GmailAccount(models.Model):
    """One connected Gmail account. The OAuth token (read-only scope) is stored encrypted."""

    tag = models.SlugField(max_length=32, unique=True)
    address_hint = models.CharField(max_length=64, blank=True)  # e.g. "tam***@gmail.com"
    token_encrypted = models.TextField()
    last_seen_ms = models.BigIntegerField(default=0)  # newest message already read
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tag


class StatementAttachment(models.Model):
    """A PDF attached to a bank email. Downloaded and read by the statement import (part B)."""

    class Status(models.TextChoices):
        PENDING = "pending"
        DONE = "done"
        SKIPPED = "skipped"
        FAILED = "failed"

    raw = models.ForeignKey("ingest.RawMessage", on_delete=models.CASCADE, related_name="attachments")
    account = models.ForeignKey(GmailAccount, on_delete=models.CASCADE, related_name="attachments")
    gmail_message_id = models.CharField(max_length=64)
    attachment_id = models.TextField()
    filename = models.CharField(max_length=255)
    size = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["gmail_message_id", "filename"], name="statement_attachment_unique"),
        ]
