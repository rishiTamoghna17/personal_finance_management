"""Map an account's last four digits to the Firefly account that owns them."""
from dataclasses import dataclass

from django.core.cache import cache

from firefly.client import FireflyClient

_CACHE_KEY = "ingest:account-directory"
_CACHE_SECONDS = 300


@dataclass(frozen=True)
class OwnAccount:
    id: str
    name: str
    is_card: bool


def _last4(number):
    digits = "".join(ch for ch in number or "" if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def _directory(refresh=False):
    if not refresh:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return cached
    client = FireflyClient.from_settings()
    directory = {}
    for kind in ("asset", "liabilities"):
        for item in client.list_accounts(kind):
            attrs = item["attributes"]
            last4 = _last4(attrs.get("account_number"))
            if not last4 or attrs.get("active") is False:
                continue
            directory.setdefault(last4, []).append(
                {"id": str(item["id"]), "name": attrs.get("name", ""), "is_card": attrs.get("account_role") == "ccAsset"}
            )
    cache.set(_CACHE_KEY, directory, _CACHE_SECONDS)
    return directory


def resolve(last4):
    """Return (OwnAccount, "") or (None, reason). Raises FireflyError if Firefly is down."""
    if not last4:
        return None, "no account digits"

    def lookup(directory):
        if len(last4) == 4:
            return directory.get(last4)
        # Fewer digits (ICICI SMS show three, SBI Card statements two): every account whose last four end with them.
        found = [acct for key, accts in directory.items() if key.endswith(last4) for acct in accts]
        return found or None

    matches = lookup(_directory())
    if matches is None:
        matches = lookup(_directory(refresh=True))  # an account may have been added since
    if not matches:
        return None, f"no Firefly account ends in {last4}"
    if len(matches) > 1:
        return None, f"{len(matches)} Firefly accounts end in {last4}"
    return OwnAccount(**matches[0]), ""
