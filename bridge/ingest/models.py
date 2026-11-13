"""Ingestion records. Money is integer paise; the ledger itself lives in Firefly."""
import uuid

from django.db import models


class RawMessage(models.Model):
    """Every message that passed the OTP filter, exactly as received."""

    class Source(models.TextChoices):
        SMS = "sms"
        EMAIL = "email"
        PDF = "pdf"
        CSV = "csv"

    class Status(models.TextChoices):
        RECEIVED = "received"  # stored, not processed yet
        PARSED = "parsed"  # linked to a ledger entry
        IGNORED = "ignored"  # deliberately not a transaction; see status_reason
        REVIEW = "review"  # needs the owner; see ReviewItem

    source = models.CharField(max_length=8, choices=Source.choices)
    sender = models.CharField(max_length=255)
    header = models.CharField(max_length=128, db_index=True)
    body = models.TextField()
    sent_at = models.DateTimeField()
    received_at = models.DateTimeField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    status_reason = models.CharField(max_length=200, blank=True)
    pattern_ref = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"raw#{self.pk} {self.header} {self.status}"


class LedgerEntry(models.Model):
    """One real payment. Many messages may point at it; it becomes one Firefly transaction."""

    class Type(models.TextChoices):
        WITHDRAWAL = "withdrawal"
        DEPOSIT = "deposit"
        TRANSFER = "transfer"

    class Status(models.TextChoices):
        PENDING = "pending"  # waiting out the settle window
        POSTING = "posting"
        POSTED = "posted"
        CANCELLED = "cancelled"  # e.g. a debit that was reversed before posting
        REVIEW = "review"

    external_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    type = models.CharField(max_length=16, choices=Type.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    amount_paise = models.BigIntegerField()
    occurred_at = models.DateTimeField()
    source_account_id = models.CharField(max_length=32, blank=True)
    destination_account_id = models.CharField(max_length=32, blank=True)
    counterparty = models.CharField(max_length=200, blank=True)
    channel = models.CharField(max_length=16, blank=True)
    reference = models.CharField(max_length=64, blank=True)
    awaiting_partner = models.BooleanField(default=False)
    is_reversal = models.BooleanField(default=False)
    category = models.CharField(max_length=64, blank=True)  # set when the bridge knows it (salary, interest, cash)
    firefly_group_id = models.CharField(max_length=32, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"entry#{self.pk} {self.type} {self.status}"


class ParsedTransaction(models.Model):
    class Direction(models.TextChoices):
        DEBIT = "debit"
        CREDIT = "credit"

    class Kind(models.TextChoices):
        PAYMENT = "payment"
        REFUND = "refund"
        REVERSAL = "reversal"
        OWN_TRANSFER = "own_transfer"  # money moving between own accounts
        CARD_PAYMENT = "card_payment"  # credit card bill payment, either side

    raw = models.OneToOneField(RawMessage, on_delete=models.CASCADE, related_name="parsed")
    entry = models.ForeignKey(LedgerEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    pattern_ref = models.CharField(max_length=128)
    amount_paise = models.BigIntegerField()
    direction = models.CharField(max_length=8, choices=Direction.choices)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PAYMENT)
    channel = models.CharField(max_length=16, blank=True)
    account_last4 = models.CharField(max_length=4, blank=True)
    firefly_account_id = models.CharField(max_length=32, blank=True, db_index=True)
    target_last4 = models.CharField(max_length=4, blank=True)  # e.g. the card a bill payment went to
    counterparty = models.CharField(max_length=200, blank=True)
    vpa = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=64, blank=True, db_index=True)
    occurred_at = models.DateTimeField(db_index=True)
    category = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"parsed#{self.pk} {self.direction} {self.amount_paise}"


class BalanceObservation(models.Model):
    """A balance the bank itself reported, e.g. "Avl bal" in an SMS."""

    firefly_account_id = models.CharField(max_length=32, db_index=True)
    balance_paise = models.BigIntegerField()
    observed_at = models.DateTimeField()
    raw = models.ForeignKey(RawMessage, on_delete=models.CASCADE, related_name="balances")


class ReviewItem(models.Model):
    class Reason(models.TextChoices):
        UNKNOWN_SENDER = "unknown_sender"
        UNPARSED = "unparsed"
        UNKNOWN_ACCOUNT = "unknown_account"
        AMBIGUOUS_MATCH = "ambiguous_match"
        TRANSFER_ALREADY_POSTED = "transfer_already_posted"
        UNPAIRED_TRANSFER = "unpaired_transfer"
        POST_FAILED = "post_failed"
        CARD_DUE_UNPAID = "card_due_unpaid"  # M5: a card's due date passed without the minimum paid

    class Status(models.TextChoices):
        OPEN = "open"
        RESOLVED = "resolved"
        IGNORED = "ignored"

    reason = models.CharField(max_length=32, choices=Reason.choices)
    detail = models.CharField(max_length=300, blank=True)
    raw = models.ForeignKey(RawMessage, null=True, blank=True, on_delete=models.CASCADE, related_name="reviews")
    entry = models.ForeignKey(LedgerEntry, null=True, blank=True, on_delete=models.CASCADE, related_name="reviews")
    candidates = models.JSONField(default=list, blank=True)  # ledger entry ids
    suggestion = models.JSONField(default=dict, blank=True)  # checked AI reading of an unparsed message (M4)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    resolution = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class DropTally(models.Model):
    """How many secret-bearing messages were dropped, per sender per day. Never the content."""

    header = models.CharField(max_length=32)
    day = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["header", "day"], name="drop_tally_header_day")]
