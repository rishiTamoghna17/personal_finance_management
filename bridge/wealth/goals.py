"""Goals from goals.yaml -> Firefly piggy banks. Progress = the money in the goal's linked accounts (capped at the
target), so it moves on its own as balances change. Pure checks here; Firefly calls in sync()."""
import datetime as dt

from django.conf import settings

from core.money import MoneyError, to_decimal_string, to_paise
from firefly.client import FireflyClient


class GoalError(ValueError):
    pass


def _date(value, field, name):
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        raise GoalError(f"{name}: {field} must be a date like 2026-12-01") from None


def average_monthly_spend(client, months, today):
    """Average spending per month over the last N whole months, leaving out CAS revaluations."""
    end = today.replace(day=1) - dt.timedelta(days=1)
    start = end.replace(day=1)
    for _ in range(months - 1):
        start = (start - dt.timedelta(days=1)).replace(day=1)
    total = sum(to_paise(amount) for name, amount in client.expense_by_payee(start, end)
                if name != settings.VALUATION_COUNTERPARTY)
    return total // months, start, end


def plan(document, client, today):
    """Validate goals.yaml; returns [{name, target_paise, start, target_date, account_ids, notes}]."""
    if not isinstance(document, dict) or not isinstance(document.get("goals"), list):
        raise GoalError("file must have a `goals:` list")
    accounts = {a["attributes"].get("name"): str(a["id"]) for a in client.list_accounts("asset")}
    goals, seen = [], set()
    for index, g in enumerate(document["goals"], start=1):
        name = (g.get("name") or "").strip() if isinstance(g, dict) else ""
        if not name:
            raise GoalError(f"goal {index}: name is required")
        if name.lower() in seen:
            raise GoalError(f"{name}: duplicate name")
        seen.add(name.lower())
        notes = ""
        if "months_of_spend" in g:
            months = g["months_of_spend"]
            if not isinstance(months, int) or not 1 <= months <= 24:
                raise GoalError(f"{name}: months_of_spend must be a whole number from 1 to 24")
            monthly, start, end = average_monthly_spend(client, settings.EMERGENCY_FUND_LOOKBACK_MONTHS, today)
            if monthly <= 0:
                raise GoalError(f"{name}: no spending recorded from {start} to {end} yet; give a fixed target instead")
            target = monthly * months
            notes = f"{months} x average monthly spend {to_decimal_string(monthly)} ({start} to {end})"
        else:
            value = g.get("target")
            if not isinstance(value, str):
                raise GoalError(f"{name}: target must be a quoted amount such as \"250000.00\"")
            try:
                target = to_paise(value)
            except MoneyError as exc:
                raise GoalError(f"{name}: target is invalid ({exc})") from None
        if target <= 0:
            raise GoalError(f"{name}: target must be more than zero")
        linked = g.get("accounts") or []
        if not linked or not all(isinstance(a, str) for a in linked):
            raise GoalError(f"{name}: list at least one account where this money is kept (accounts: [HSBC Bank])")
        missing = [a for a in linked if a not in accounts]
        if missing:
            raise GoalError(f"{name}: no Firefly asset account named {', '.join(missing)}")
        target_date = _date(g["target_date"], "target_date", name) if g.get("target_date") else None
        start = _date(g.get("start_date") or today, "start_date", name)
        if target_date and target_date <= start:
            raise GoalError(f"{name}: target_date must be after start_date")
        goals.append({"name": name, "target_paise": target, "start": start, "target_date": target_date,
                      "account_ids": [accounts[a] for a in linked], "notes": (g.get("notes") or notes)[:500]})
    return goals


def saved_per_account(client, account_ids, target_paise):
    """How much of each linked account counts toward the goal: its positive balance, until the target is reached."""
    remaining, parts = target_paise, []
    for account_id in account_ids:
        balance = to_paise(client.get_account(account_id)["attributes"].get("current_balance") or "0")
        take = max(0, min(balance, remaining))
        remaining -= take
        parts.append({"account_id": account_id, "current_amount": to_decimal_string(take)})
    return parts


def payload(goal, parts):
    body = {"name": goal["name"], "target_amount": to_decimal_string(goal["target_paise"]),
            "start_date": goal["start"].isoformat(), "transaction_currency_code": "INR", "accounts": parts,
            "notes": goal["notes"] or "Managed by the bridge from goals.yaml."}
    if goal["target_date"]:
        body["target_date"] = goal["target_date"].isoformat()
    return body


def sync(goals, client=None):
    """Create or update one piggy bank per goal. Returns [(name, "created"|"updated")]."""
    client = client or FireflyClient.from_settings()
    existing = {p["attributes"].get("name"): str(p["id"]) for p in client.list_all("piggy-banks")}
    results = []
    for goal in goals:
        body = payload(goal, saved_per_account(client, goal["account_ids"], goal["target_paise"]))
        if goal["name"] in existing:
            client.update_piggy_bank(existing[goal["name"]], body)
            results.append((goal["name"], "updated"))
        else:
            client.create_piggy_bank(body)
            results.append((goal["name"], "created"))
    return results


def refresh_progress(client=None):
    """Daily: move each bridge-managed piggy bank's saved amount to what its accounts hold now."""
    client = client or FireflyClient.from_settings()
    updated = 0
    for piggy in client.list_all("piggy-banks"):
        attrs = piggy["attributes"]
        account_ids = [str(a.get("account_id") or a.get("id")) for a in attrs.get("accounts") or []]
        if not account_ids or not attrs.get("target_amount"):
            continue
        parts = saved_per_account(client, account_ids, to_paise(attrs["target_amount"]))
        client.update_piggy_bank(str(piggy["id"]), {"accounts": parts})
        updated += 1
    return updated


def progress(today, client=None):
    """Goals as the API reports them, with what is still needed per month to hit the target date."""
    client = client or FireflyClient.from_settings()
    rows = []
    for piggy in client.list_all("piggy-banks"):
        a = piggy["attributes"]
        target = to_paise(a.get("target_amount") or "0")
        saved = to_paise(a.get("current_amount") or "0")
        left = max(0, target - saved)
        target_date = dt.date.fromisoformat(a["target_date"][:10]) if a.get("target_date") else None
        per_month = None
        if target_date and left:
            months = max(1, (target_date.year - today.year) * 12 + target_date.month - today.month
                         + (1 if target_date.day >= today.day else 0))
            per_month = -(-left // months)  # round up to the paisa
        rows.append({"id": str(piggy["id"]), "name": a.get("name"), "target_paise": target, "saved_paise": saved,
                     "left_paise": left, "percent": (saved * 100 // target) if target else 0,
                     "target_date": target_date.isoformat() if target_date else None,
                     "needed_per_month_paise": per_month})
    return rows
