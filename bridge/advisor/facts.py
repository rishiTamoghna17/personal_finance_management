"""Summaries the advisor may use. Computed by code from Firefly and the bridge; integer paise throughout.
Only summaries leave this module: category, payee and account names and totals. Never message text, account or
card numbers, or references."""
import datetime as dt

from django.conf import settings

from core.money import to_paise
from firefly.client import FireflyClient
from ingest.models import ReviewItem
from wealth import dues, goals, networth
from wealth.models import CasStatement


def month_start(day):
    return day.replace(day=1)


def previous_month(day):
    end = month_start(day) - dt.timedelta(days=1)
    return month_start(end), end


def _sum(rows):
    return sum(to_paise(r["amount"]) for r in rows)


def spending(start, end, client):
    """Spending between two dates (inclusive): total, by category and top payees. CAS revaluations left out."""
    valuation = settings.VALUATION_COUNTERPARTY
    all_payees = client.insight("expense/expense", start, end)
    payees = [r for r in all_payees if r["name"] != valuation]
    by_payee_valuation = _sum([r for r in all_payees if r["name"] == valuation])
    categories = client.insight("expense/category", start, end)
    uncategorised = max(0, _sum(client.insight("expense/no-category", start, end)) - by_payee_valuation)
    by_category = {r["name"]: to_paise(r["amount"]) for r in categories if to_paise(r["amount"])}
    if uncategorised:
        by_category["Uncategorised"] = uncategorised
    top = sorted(((r["name"], to_paise(r["amount"])) for r in payees), key=lambda x: -x[1])[:5]
    return {"start": start.isoformat(), "end": end.isoformat(), "total_paise": _sum(payees),
            "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])), "top_payees": top}


def income(start, end, client):
    rows = [r for r in client.insight("income/revenue", start, end) if r["name"] != settings.VALUATION_COUNTERPARTY]
    return {"start": start.isoformat(), "end": end.isoformat(), "total_paise": _sum(rows)}


def holdings_summary():
    cas = CasStatement.objects.order_by("-statement_date").first()
    if cas is None:
        return None
    by_kind = {}
    for h in cas.holdings.all():
        by_kind[h.kind] = by_kind.get(h.kind, 0) + h.value_paise
    items = [{"name": h.name, "kind": h.kind, "value_paise": h.value_paise}
             for h in cas.holdings.order_by("-value_paise")]
    return {"statement_date": cas.statement_date.isoformat(), "total_paise": cas.total_paise, "by_kind": by_kind,
            "holdings": items}


def fact_sheet(today, client=None):
    """Everything the advisor normally needs, in one small dict."""
    client = client or FireflyClient.from_settings()
    last_start, last_end = previous_month(today)
    # Same days of last month, for a fair "so far" comparison.
    same_days_end = min(last_end, last_start + (today - month_start(today)))
    worth = networth.compute(client=client)
    return {
        "today": today.isoformat(),
        "records_start": settings.INGEST_LEDGER_START,
        "this_month": spending(month_start(today), today, client),
        "last_month_same_days": spending(last_start, same_days_end, client),
        "last_month_full": spending(last_start, last_end, client),
        "income_this_month": income(month_start(today), today, client),
        "upcoming_30_days": dues.upcoming(30, today),
        "goals": goals.progress(today, client),
        "net_worth": {k: worth[k] for k in ("assets_paise", "liabilities_paise", "net_worth_paise")},
        "accounts": [{"name": a["name"], "kind": a["kind"], "balance_paise": a["balance_paise"],
                      "balance_status": a["balance_status"]} for a in worth["accounts"]],
        "investments": holdings_summary(),
        "open_review_items": ReviewItem.objects.filter(status=ReviewItem.Status.OPEN).count(),
    }
