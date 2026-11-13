"""Net worth = assets minus liabilities, from Firefly's balances (rule 8: a credit limit is never counted;
Firefly never holds one). Each account keeps its balance status: confirmed, stale or calculated."""
import datetime as dt

from django.utils import timezone

from firefly.client import FireflyClient
from firefly.views import _bank_balances, serialize_account

from .models import NetWorthSnapshot


def compute(on_date=None, client=None):
    client = client or FireflyClient.from_settings()
    items = [i for i in client.list_accounts("asset", on_date) + client.list_accounts("liabilities", on_date)
             if i["attributes"].get("active") is not False and i["attributes"].get("include_net_worth") is not False]
    observations = _bank_balances([str(i["id"]) for i in items]) if on_date is None else {}
    assets = liabilities = 0
    rows = []
    for item in items:
        row = serialize_account(item, observations.get(str(item["id"])))
        balance = row["balance_paise"] or 0
        if row["kind"] == "liability":
            owed = abs(balance)  # a loan is never in credit; Firefly may sign it either way
            liabilities += owed
            balance = -owed
        elif balance >= 0:
            assets += balance
        else:
            liabilities += -balance  # card dues, or a bank account below zero
        rows.append({"id": row["id"], "name": row["name"], "kind": row["kind"], "balance_paise": balance,
                     "balance_status": row["balance_status"] if on_date is None else "calculated"})
    return {"assets_paise": assets, "liabilities_paise": liabilities, "net_worth_paise": assets - liabilities,
            "accounts": rows}


def snapshot(on_date, client=None):
    """Store the net worth at the end of on_date. Re-running for the same date replaces it."""
    data = compute(on_date, client)
    snap, _ = NetWorthSnapshot.objects.update_or_create(taken_on=on_date, defaults=data)
    return snap


def last_month_end(today=None):
    today = today or timezone.localdate()
    return today.replace(day=1) - dt.timedelta(days=1)
