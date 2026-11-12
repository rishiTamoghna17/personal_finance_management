from rest_framework.response import Response
from rest_framework.views import APIView

from core.money import MoneyError, to_paise

from .client import FireflyClient, FireflyError

_LIABILITY_TYPES = {"liability", "liabilities", "loan", "debt", "mortgage"}


def _last4(account_number):
    digits = "".join(ch for ch in (account_number or "") if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else None


def serialize_account(item):
    attrs = item["attributes"]
    kind = "liability" if attrs.get("type") in _LIABILITY_TYPES else "asset"
    if attrs.get("account_role") == "ccAsset":
        kind = "credit_card"
    try:
        balance_paise = to_paise(attrs.get("current_balance") or "0")
    except MoneyError:
        balance_paise = None
    return {
        "id": str(item["id"]),
        "name": attrs.get("name"),
        "kind": kind,
        "role": attrs.get("account_role"),
        "liability_type": attrs.get("liability_type"),
        "last4": _last4(attrs.get("account_number")),
        "currency": attrs.get("currency_code"),
        # What Firefly's ledger adds up to. For a card or loan this is negative: money owed.
        "balance_paise": balance_paise,
        # M1 has no bank-confirmed balances yet; "confirmed" and "stale" arrive with ingestion.
        "balance_status": "calculated" if balance_paise is not None else "unknown",
        "active": attrs.get("active"),
        "include_net_worth": attrs.get("include_net_worth"),
    }


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
        return Response({"accounts": [serialize_account(i) for i in items]})
