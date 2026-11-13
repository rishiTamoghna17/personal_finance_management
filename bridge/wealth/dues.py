"""Card dues and EMIs coming up, and dues that passed unpaid."""
import datetime as dt

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ingest.models import LedgerEntry, ParsedTransaction, ReviewItem

from .models import CardDue, EmiPlan

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def payments_since(due):
    start = dt.datetime.combine(due.statement_date + dt.timedelta(days=1), dt.time(0, 0), tzinfo=IST)
    end = dt.datetime.combine(due.due_date, dt.time(23, 59, 59), tzinfo=IST)
    # One payment may be reported by SMS, email and statement: count each ledger entry once (rule 6).
    entry_ids = set(ParsedTransaction.objects.filter(
        firefly_account_id=due.firefly_account_id, direction="credit", occurred_at__range=(start, end),
        entry__isnull=False).exclude(entry__status=LedgerEntry.Status.CANCELLED).values_list("entry_id", flat=True))
    return LedgerEntry.objects.filter(pk__in=entry_ids).aggregate(s=Sum("amount_paise"))["s"] or 0


def check_dues(today=None):
    """Due dates that have passed: paid if payments on the card since the statement reach the minimum due,
    otherwise a review item. Statements from before the ledger start are not judged (payments then are unknown)."""
    today = today or timezone.localdate()
    start = dt.date.fromisoformat(settings.INGEST_LEDGER_START)
    counts = {"paid": 0, "unpaid": 0}
    for due in CardDue.objects.filter(status=CardDue.Status.OPEN, due_date__lt=today, statement_date__gte=start):
        paid = payments_since(due)
        needed = due.minimum_due_paise if due.minimum_due_paise is not None else due.total_due_paise
        with transaction.atomic():
            due.paid_paise = paid
            if paid >= needed:
                due.status = CardDue.Status.PAID
                counts["paid"] += 1
            else:
                due.status = CardDue.Status.UNPAID
                counts["unpaid"] += 1
                ReviewItem.objects.create(
                    reason=ReviewItem.Reason.CARD_DUE_UNPAID, raw=due.attachment.raw,
                    detail=f"card account {due.firefly_account_id}: due {due.due_date}, minimum {needed} paise, "
                           f"payments seen {paid} paise",
                )
            due.save(update_fields=["paid_paise", "status"])
    return counts


def upcoming(days=30, today=None):
    today = today or timezone.localdate()
    until = today + dt.timedelta(days=days)
    items = []
    for due in CardDue.objects.filter(due_date__range=(today, until)).exclude(status=CardDue.Status.PAID):
        items.append({"type": "card_due", "date": due.due_date.isoformat(), "account_id": due.firefly_account_id,
                      "amount_paise": due.total_due_paise, "minimum_paise": due.minimum_due_paise})
    for due in CardDue.objects.filter(status=CardDue.Status.UNPAID):
        items.append({"type": "card_due_unpaid", "date": due.due_date.isoformat(), "account_id": due.firefly_account_id,
                      "amount_paise": due.total_due_paise, "minimum_paise": due.minimum_due_paise})
    for plan in EmiPlan.objects.all():
        for row in plan.schedule:
            day = dt.date.fromisoformat(row["date"])
            if today <= day <= until and row["emi_paise"] > 0:
                left = sum(1 for r in plan.schedule if r["emi_paise"] > 0 and dt.date.fromisoformat(r["date"]) >= day)
                items.append({"type": "emi", "date": row["date"], "account_id": plan.firefly_account_id,
                              "name": plan.name, "amount_paise": row["emi_paise"], "instalments_left": left})
    return sorted(items, key=lambda i: i["date"])
