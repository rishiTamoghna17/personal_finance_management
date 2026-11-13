"""Turn accounts.yaml into Firefly account payloads. Pure functions, no I/O."""
import datetime as dt
import re

from core.money import MoneyError, to_decimal_string, to_paise

CURRENCY = "INR"
BANK_ROLES = {"savings": "savingAsset", "salary": "defaultAsset", "current": "defaultAsset"}
KINDS = {"bank", "credit_card", "loan", "cash"}


class SeedError(ValueError):
    pass


def _date(value, field, name):
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise SeedError(f"{name}: {field} must be a date like \"2026-11-01\"")


def _paise(value, field, name):
    if not isinstance(value, str):
        raise SeedError(f"{name}: {field} must be a quoted string such as \"1234.50\"")
    try:
        paise = to_paise(value)
    except MoneyError as exc:
        raise SeedError(f"{name}: {field} is invalid ({exc})") from None
    if paise < 0:
        raise SeedError(f"{name}: {field} must not be negative")
    return paise


def _account_number(entry, name):
    last4 = entry.get("last4")
    if last4 is None:
        return None
    if not isinstance(last4, str) or not re.fullmatch(r"\d{4}", last4):
        raise SeedError(f"{name}: last4 must be exactly four digits in quotes, never a full number")
    return f"XX{last4}"


def _percent(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,2}(\.\d{1,4})?", value):
        raise SeedError(f"{name}: interest_rate_percent must be a quoted string such as \"9.50\"")
    return value


def build_plan(document):
    """Validate the parsed YAML and return (payloads_to_create, planned_names).

    planned_names are loans marked `status: planned`: reported, never sent to Firefly.
    """
    if not isinstance(document, dict) or not isinstance(document.get("accounts"), list):
        raise SeedError("file must have an `accounts:` list")
    opening_date = _date(document.get("opening_balance_date"), "opening_balance_date", "file")

    payloads, planned, seen = [], [], set()
    for index, entry in enumerate(document["accounts"], start=1):
        if not isinstance(entry, dict):
            raise SeedError(f"entry {index}: must be a mapping")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SeedError(f"entry {index}: name is required")
        name = name.strip()
        if name.lower() in seen:
            raise SeedError(f"{name}: duplicate name")
        seen.add(name.lower())
        kind = entry.get("kind")
        if kind not in KINDS:
            raise SeedError(f"{name}: kind must be one of {sorted(KINDS)}")

        payload = {"name": name, "currency_code": CURRENCY, "active": True, "include_net_worth": True}
        number = _account_number(entry, name)
        if number:
            payload["account_number"] = number

        if kind == "cash":
            payload.update(type="asset", account_role="cashWalletAsset")
            payload.pop("account_number", None)
            balance = _paise(entry.get("opening_balance"), "opening_balance", name)
        elif kind == "bank":
            role = entry.get("role")
            if role not in BANK_ROLES:
                raise SeedError(f"{name}: role must be one of {sorted(BANK_ROLES)}")
            payload.update(type="asset", account_role=BANK_ROLES[role])
            balance = _paise(entry.get("opening_balance"), "opening_balance", name)
        elif kind == "credit_card":
            payload.update(
                type="asset",
                account_role="ccAsset",
                credit_card_type="monthlyFull",
                monthly_payment_date=_date(entry.get("next_payment_due"), "next_payment_due", name),
            )
            # Money owed on a card is a negative balance on the card account.
            balance = -_paise(entry.get("outstanding"), "outstanding", name)
        else:  # loan
            status = entry.get("status")
            if status not in ("planned", "active"):
                raise SeedError(f"{name}: status must be planned or active")
            if status == "planned":
                planned.append(name)
                continue
            payload.update(
                type="liability",
                liability_type="loan",
                liability_direction="debit",  # "debit" = I owe this money
                interest=_percent(entry.get("interest_rate_percent"), name),
                interest_period="yearly",
            )
            balance = _paise(entry.get("outstanding"), "outstanding", name)

        # Always sent, even when zero, so re-running the seed can also correct an earlier value.
        payload["opening_balance"] = to_decimal_string(balance)
        payload["opening_balance_date"] = opening_date
        payloads.append(payload)
    return payloads, planned


def needs_update(payload, attrs):
    """Does an existing Firefly account differ from accounts.yaml in number or opening balance?"""
    def paise(value):
        try:
            return to_paise(str(value)) if value not in (None, "") else 0
        except MoneyError:
            return None

    if (attrs.get("name") or "").strip() != payload["name"]:
        return True
    if (attrs.get("account_number") or None) != payload.get("account_number"):
        return True
    if paise(attrs.get("opening_balance")) != to_paise(payload["opening_balance"]):
        return True
    have_date = (attrs.get("opening_balance_date") or "")[:10]
    return to_paise(payload["opening_balance"]) != 0 and have_date != payload["opening_balance_date"]
