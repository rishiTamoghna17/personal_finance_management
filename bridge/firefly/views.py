from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from core.money import MoneyError, to_paise

from .client import FireflyClient, FireflyError

_LIABILITY_TYPES = {"liability", "liabilities", "loan", "debt", "mortgage"}


def _last4(account_number):
    digits = "".join(ch for ch in (account_number or "") if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else None


def _bank_balances(account_ids):
    from ingest.models import BalanceObservation

    latest = {}
    for obs in BalanceObservation.objects.filter(firefly_account_id__in=account_ids).order_by("observed_at"):
        latest[obs.firefly_account_id] = obs
    return latest


def serialize_account(item, observation=None):
    attrs = item["attributes"]
    kind = "liability" if attrs.get("type") in _LIABILITY_TYPES else "asset"
    if attrs.get("account_role") == "ccAsset":
        kind = "credit_card"
    try:
        balance_paise = to_paise(attrs.get("current_balance") or "0")
    except MoneyError:
        balance_paise = None
    result = {
        "id": str(item["id"]),
        "name": attrs.get("name"),
        "kind": kind,
        "role": attrs.get("account_role"),
        "liability_type": attrs.get("liability_type"),
        "last4": _last4(attrs.get("account_number")),
        "currency": attrs.get("currency_code"),
        # What Firefly's ledger adds up to. For a card or loan this is negative: money owed.
        "balance_paise": balance_paise,
        # calculated: only Firefly's ledger sum. confirmed / stale: the bank itself reported a balance.
        "balance_status": "calculated" if balance_paise is not None else "unknown",
        "bank_balance": None,
        "active": attrs.get("active"),
        "include_net_worth": attrs.get("include_net_worth"),
    }
    if observation is not None:
        age = timezone.now() - observation.observed_at
        fresh = age.total_seconds() <= settings.BALANCE_CONFIRMED_HOURS * 3600
        result["balance_status"] = "confirmed" if fresh else "stale"
        result["bank_balance"] = {
            "balance_paise": observation.balance_paise,
            "observed_at": observation.observed_at.isoformat(),
        }
    return result


class AccountsView(APIView):
    """GET /api/v1/accounts - own accounts, cards and loans, read from Firefly."""

    def get(self, request):
        client = FireflyClient.from_settings()
        if not client.has_token:
            return Response({"detail": "FIREFLY_ACCESS_TOKEN is not set."}, status=503)
        try:
            items = client.list_accounts("asset") + client.list_accounts("liabilities")
        except FireflyError:
            return Response({"detail": "Firefly is unavailable."}, status=502)
        observations = _bank_balances([str(i["id"]) for i in items])
        return Response({"accounts": [serialize_account(i, observations.get(str(i["id"]))) for i in items]})
