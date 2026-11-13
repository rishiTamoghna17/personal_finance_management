"""M5: card dues, EMI plans, investment holdings (as stated by CAS) and monthly net worth snapshots.
Money is integer paise. Nothing here is a balance Firefly does not already hold, except holdings detail."""
from django.db import models


class CardDue(models.Model):
    """What a card statement says is due, and by when."""

    class Status(models.TextChoices):
        OPEN = "open"
        PAID = "paid"  # payments on the card since the statement reached the minimum due
        UNPAID = "unpaid"  # due date passed without that; a review item was raised

    attachment = models.OneToOneField("mail.StatementAttachment", on_delete=models.CASCADE, related_name="card_due")
    firefly_account_id = models.CharField(max_length=32, db_index=True)
    statement_date = models.DateField()
    due_date = models.DateField(db_index=True)
    total_due_paise = models.BigIntegerField()
    minimum_due_paise = models.BigIntegerField(null=True, blank=True)
    paid_paise = models.BigIntegerField(default=0)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN, db_index=True)


class EmiPlan(models.Model):
    """A loan or a card purchase converted to EMIs, with its schedule."""

    source = models.CharField(max_length=32)  # axis-emi-letter | accounts.yaml
    attachment = models.OneToOneField("mail.StatementAttachment", null=True, blank=True, on_delete=models.CASCADE,
                                      related_name="emi_plan")
    firefly_account_id = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=160)
    reference_tail = models.CharField(max_length=8, blank=True)
    principal_paise = models.BigIntegerField()
    rate_text = models.CharField(max_length=32, blank=True)
    # [{"number", "date", "emi_paise", "principal_paise", "interest_paise"}], date as ISO text
    schedule = models.JSONField(default=list)
    firefly_bill_id = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CasStatement(models.Model):
    attachment = models.OneToOneField("mail.StatementAttachment", on_delete=models.CASCADE, related_name="cas")
    statement_date = models.DateField(db_index=True)
    total_paise = models.BigIntegerField()
    applied_to_firefly = models.BooleanField(default=False)


class Holding(models.Model):
    cas = models.ForeignKey(CasStatement, on_delete=models.CASCADE, related_name="holdings")
    kind = models.CharField(max_length=16)  # mutual_fund | stock | other
    isin = models.CharField(max_length=16, blank=True)
    name = models.CharField(max_length=200)
    units = models.CharField(max_length=32)
    price = models.CharField(max_length=32)
    value_paise = models.BigIntegerField()


class NetWorthSnapshot(models.Model):
    taken_on = models.DateField(unique=True)
    assets_paise = models.BigIntegerField()
    liabilities_paise = models.BigIntegerField()  # positive number: what is owed
    net_worth_paise = models.BigIntegerField()
    # [{"id", "name", "kind", "balance_paise", "balance_status"}]
    accounts = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now=True)
