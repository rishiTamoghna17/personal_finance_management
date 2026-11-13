"""Weekly digest (Monday to Sunday): numbers and wording both from code, so nothing in it can be invented."""
import datetime as dt

from django.conf import settings
from django.utils import timezone

from firefly.client import FireflyClient
from wealth import dues, goals
from wealth.models import NetWorthSnapshot

from . import facts
from .render import inr


def week_bounds(week=None, today=None):
    """'2026-W46' -> (Monday, Sunday). Default: the last complete week."""
    if week:
        year, number = week.upper().split("-W")
        monday = dt.date.fromisocalendar(int(year), int(number), 1)
    else:
        today = today or timezone.localdate()
        monday = today - dt.timedelta(days=today.weekday() + 7)
    return monday, monday + dt.timedelta(days=6)


def build(week=None, today=None, client=None):
    today = today or timezone.localdate()
    client = client or FireflyClient.from_settings()
    monday, sunday = week_bounds(week, today)
    this_week = facts.spending(monday, sunday, client)
    prev_week = facts.spending(monday - dt.timedelta(days=7), sunday - dt.timedelta(days=7), client)
    month_to_date = facts.spending(facts.month_start(sunday), sunday, client)
    last_start, last_end = facts.previous_month(sunday)
    same_days = facts.spending(last_start, min(last_end, last_start + (sunday - facts.month_start(sunday))), client)
    upcoming = dues.upcoming(14, today)
    goal_rows = goals.progress(today, client)
    snaps = list(NetWorthSnapshot.objects.order_by("-taken_on")[:2])
    worth = {"latest": None, "change_paise": None}
    if snaps:
        worth["latest"] = {"date": snaps[0].taken_on.isoformat(), "net_worth_paise": snaps[0].net_worth_paise}
        if len(snaps) == 2:
            worth["change_paise"] = snaps[0].net_worth_paise - snaps[1].net_worth_paise

    ledger_start = dt.date.fromisoformat(settings.INGEST_LEDGER_START)

    def versus(label, data):
        if dt.date.fromisoformat(data["start"]) < ledger_start:
            return f"{label}: not tracked (records start {ledger_start:%d %b %Y})"
        return f"{label} {inr(data['total_paise'])}"

    lines = [f"Week {monday:%d %b} to {sunday:%d %b %Y}: you spent {inr(this_week['total_paise'])} "
             f"({versus('previous week', prev_week)})."]
    top = list(this_week["by_category"].items())[:3]
    if top:
        lines.append("Top categories: " + ", ".join(f"{n} {inr(v)}" for n, v in top) + ".")
    lines.append(f"This month so far {inr(month_to_date['total_paise'])} "
                 f"({versus('same days last month', same_days)}).")
    if upcoming:
        lines.append("Due in the next 14 days: " + "; ".join(
            f"{i['date']} {'EMI' if i['type'] == 'emi' else 'card bill'} {inr(i['amount_paise'])}" for i in upcoming) + ".")
    for g in goal_rows:
        pace = f"; {inr(g['needed_per_month_paise'])} a month needed" if g.get("needed_per_month_paise") else ""
        lines.append(f"Goal {g['name']}: {inr(g['saved_paise'])} of {inr(g['target_paise'])} ({g['percent']}%){pace}.")
    if worth["change_paise"] is not None:
        lines.append(f"Net worth at the last month end: {inr(worth['latest']['net_worth_paise'])} "
                     f"({'up' if worth['change_paise'] >= 0 else 'down'} {inr(abs(worth['change_paise']))}).")
    return {"week": f"{monday.isocalendar().year}-W{monday.isocalendar().week:02d}", "start": monday.isoformat(),
            "end": sunday.isoformat(), "spending": this_week, "previous_week": prev_week,
            "month_to_date": month_to_date, "last_month_same_days": same_days, "upcoming_14_days": upcoming,
            "goals": goal_rows, "net_worth": worth, "text": "\n".join(lines)}
