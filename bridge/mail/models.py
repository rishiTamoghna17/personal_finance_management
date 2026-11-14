from django.db import models


class GmailAccount(models.Model):
    """One connected Gmail account. The OAuth token (read-only scope) is stored encrypted."""

    tag = models.SlugField(max_length=32, unique=True)
    address_hint = models.CharField(max_length=64, blank=True)  # e.g. "tam***@gmail.com"
    token_encrypted = models.TextField()
    last_seen_ms = models.BigIntegerField(default=0)  # newest message already read
    # When the owner last signed in. A Google app in "Testing" loses its tokens 7 days after sign-in (M7 reminder).
    connected_at = models.DateTimeField(null=True, blank=True)
    # SHA-256 of the Google address, to make sure a reconnect signs in to the same mailbox (never stored in clear).
    email_hash = models.CharField(max_length=64, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tag


class StatementAttachment(models.Model):
    """A PDF attached to a bank email. Downloaded and read by the statement import (part B)."""

    class Status(models.TextChoices):
        PENDING = "pending"  # recorded, not downloaded
        DOWNLOADED = "downloaded"
        NEEDS_PASSWORD = "needs_password"  # no saved password opens it yet
        NEEDS_PARSER = "needs_parser"  # opens, but no parser for this layout yet
        DONE = "done"
        SKIPPED = "skipped"
        FAILED = "failed"

    # Null for statements fetched by the backfill command (older than the ledger start).
    raw = models.ForeignKey("ingest.RawMessage", null=True, blank=True, on_delete=models.CASCADE, related_name="attachments")
    key = models.SlugField(max_length=32, blank=True)  # statement password key: hsbc, icici, axis, sbi-card, hdfc
    subject = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    local_file = models.CharField(max_length=300, blank=True)  # the PDF exactly as the bank sent it (still locked)
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


class GoogleCredential(models.Model):
    """A Google sign-in that is not a Gmail account: today only "drive" (encrypted backups)."""

    name = models.SlugField(max_length=32, unique=True)
    token_encrypted = models.TextField()
    client = models.CharField(max_length=8)  # which web client (Google project) issued it
    email_hash = models.CharField(max_length=64, blank=True)
    connected_at = models.DateTimeField()


class ReconnectLink(models.Model):
    """A one-time link that lets the owner renew a Google sign-in from the phone. Valid 24 hours, single use.
    The link token is stored encrypted (to show it in the alert) and hashed (to look it up)."""

    connection = models.CharField(max_length=40, db_index=True)  # "gmail:acct1" | "gmail:acct2" | "drive"
    token_hash = models.CharField(max_length=64, unique=True)
    token_encrypted = models.TextField()
    oauth_state = models.CharField(max_length=64, blank=True, db_index=True)
    code_verifier = models.TextField(blank=True)  # PKCE, encrypted
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
