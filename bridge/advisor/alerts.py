"""Alerts by fixed rules (no model). Each alert: type, severity (high | medium | low), message, data."""
import datetime as dt

from django.conf import settings
from django.utils import timezone

from firefly.client import FireflyClient
from ingest.models import ReviewItem
from wealth import dues, goals
from wealth.models import CardDue, CasStatement

from . import facts
from .render import inr

SPIKE_FACTOR_NUM, SPIKE_FACTOR_DEN = 3, 2  # 1.5x
SPIKE_MIN_PAISE = 100000  # ignore categories under Rs 1,000 this month
CAS_STALE_DAYS = 45
DUE_SOON_DAYS = 3


def _whole_months_since_start(today, count):
    """Up to `count` whole months before this one, all on or after the ledger start."""
    start = dt.date.fromisoformat(settings.INGEST_LEDGER_START)
    months, end = [], facts.month_start(today) - dt.timedelta(days=1)
    while len(months) < count:
        first = facts.month_start(end)
        if first < start:
            break
        months.append((first, end))
        end = first - dt.timedelta(days=1)
    return months


def category_spikes(today, client):
    months = _whole_months_since_start(today, 3)
    if not months:
        return []  # not enough history yet: no comparison is better than a wrong one
    totals = {}
    for first, last in months:
        for name, paise in facts.spending(first, last, client)["by_category"].items():
            totals[name] = totals.get(name, 0) + paise
    now = facts.spending(facts.month_start(today), today, client)["by_category"]
    out = []
    for name, paise in now.items():
        average = totals.get(name, 0) // len(months)
        if paise >= SPIKE_MIN_PAISE and average and paise * SPIKE_FACTOR_DEN > average * SPIKE_FACTOR_NUM:
            out.append({"type": "category_spike", "severity": "medium",
                        "message": f"{name}: {inr(paise)} so far this month, above 1.5 times your usual {inr(average)} a month.",
                        "data": {"category": name, "this_month_paise": paise, "average_paise": average}})
    return out


def goals_behind(today, client):
    out = []
    for g in goals.progress(today, client):
        piggy_start = g.get("start_date")
        if not (g.get("target_date") and piggy_start) or not g["left_paise"]:
            continue
        start, end = dt.date.fromisoformat(piggy_start), dt.date.fromisoformat(g["target_date"])
        span, done = (end - start).days, (today - start).days
        if span <= 0 or done <= 0:
            continue
        expected = g["target_paise"] * min(done, span) // span
        if g["saved_paise"] * 10 < expected * 9:
            out.append({"type": "goal_behind", "severity": "medium",
                        "message": f"Goal {g['name']}: {inr(g['saved_paise'])} saved, about {inr(expected)} expected by now.",
                        "data": {"goal": g["name"], "saved_paise": g["saved_paise"], "expected_paise": expected}})
    return out


def build(today=None, client=None):
    today = today or timezone.localdate()
    client = client or FireflyClient.from_settings()
    alerts = []
    for due in CardDue.objects.filter(status=CardDue.Status.UNPAID):
        alerts.append({"type": "card_due_unpaid", "severity": "high",
                       "message": f"A card bill of {inr(due.total_due_paise)} was due on {due.due_date:%d %b} and no "
                                  f"payment covering the minimum was seen.",
                       "data": {"account_id": due.firefly_account_id, "due_date": due.due_date.isoformat()}})
    for item in dues.upcoming(DUE_SOON_DAYS, today):
        if item["type"] in ("emi", "card_due"):
            what = "EMI" if item["type"] == "emi" else "Card bill"
            alerts.append({"type": "due_soon", "severity": "medium",
                           "message": f"{what} of {inr(item['amount_paise'])} due on {item['date']}.", "data": item})
    alerts += category_spikes(today, client)
    alerts += goals_behind(today, client)
    open_items = ReviewItem.objects.filter(status=ReviewItem.Status.OPEN).count()
    if open_items:
        alerts.append({"type": "review_waiting", "severity": "low",
                       "message": f"{open_items} item{'s' if open_items != 1 else ''} waiting in the review queue.",
                       "data": {"count": open_items}})
    cas = CasStatement.objects.order_by("-statement_date").first()
    if cas and (today - cas.statement_date).days > CAS_STALE_DAYS:
        alerts.append({"type": "investments_stale", "severity": "low",
                       "message": f"Investment values are from {cas.statement_date:%d %b %Y}; the newer CDSL statement "
                                  f"has not been read yet.", "data": {"statement_date": cas.statement_date.isoformat()}})
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(alerts, key=lambda a: order[a["severity"]])
