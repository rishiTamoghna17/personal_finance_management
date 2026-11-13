"""SIP and fund purchases are moves of your own money into investments, not spending."""
import re

from django.conf import settings
from django.core.cache import cache

from firefly.client import FireflyClient

_KEY = "wealth:mf-account-id"


def mutual_fund_account_id():
    """The Firefly id of the mutual funds account, or "" until a CAS has created it."""
    cached = cache.get(_KEY)
    if cached is not None:
        return cached
    name = settings.INVESTMENT_ACCOUNTS["mutual_fund"]
    found = next((str(a["id"]) for a in FireflyClient.from_settings().list_accounts("asset")
                  if a["attributes"].get("name") == name), "")
    cache.set(_KEY, found, 300)
    return found


def is_investment_payee(counterparty):
    return bool(counterparty) and re.search(settings.INVESTMENT_PAYEE_REGEX, counterparty, re.IGNORECASE) is not None
