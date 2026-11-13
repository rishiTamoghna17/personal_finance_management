"""Read a bank message no profile understands. The answer is only ever a suggestion for the owner to accept,
and it is checked against the original text first: the model may not invent an amount, account or date."""
import datetime as dt
import re

from core.money import MoneyError, to_paise
from ingest.parser import IST

from . import masking, providers

SYSTEM = (
    "You read one message from an Indian bank or card issuer. Reply with JSON only, with these keys: "
    '"is_transaction" (true if money actually moved: money paid, spent, withdrawn or debited, AND money received, '
    'got or credited all count), "amount" (exactly as written, e.g. "1,234.50"), '
    '"direction" ("debit" if money left the account or card, "credit" if it came in), '
    '"account_digits" (the account or card digits exactly as written, e.g. "XX1234" or "378"), '
    '"date" ("YYYY-MM-DD" or null), "counterparty" (who was paid or who paid, or null), '
    '"reference" (the transaction reference as written, or null). '
    "Use only what is in the message. Placeholders like <REF1> or <VPA1> stand for hidden values; copy them as they are. "
    'If the message is an OTP, offer, reminder, failed or declined payment, or anything unclear, set "is_transaction" to false.'
)


class Rejected(Exception):
    pass


def _amounts_in(text):
    """Every number written in the message, as paise (so "250", "250.00" and "2,50.00" compare equal)."""
    found = set()
    for token in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            found.add(to_paise(token.rstrip(".")))
        except MoneyError:
            continue
    return found


def _digits(text):
    return re.sub(r"\D", "", text or "")


def check(answer, original, sent_at):
    """Turn a model answer into a suggestion, or raise Rejected with the reason."""
    if not isinstance(answer, dict) or answer.get("is_transaction") is not True:
        raise Rejected("model says this is not a transaction")
    amount_text = str(answer.get("amount") or "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    try:
        amount = to_paise(amount_text)
    except MoneyError:
        raise Rejected("amount is not a number") from None
    if amount <= 0 or amount not in _amounts_in(original):
        raise Rejected("amount does not appear in the message")
    if answer.get("direction") not in ("debit", "credit"):
        raise Rejected("direction is neither debit nor credit")
    digits = _digits(answer.get("account_digits"))[-4:]
    if len(digits) < 3 or digits not in _digits(original):
        raise Rejected("account digits do not appear in the message")
    occurred = sent_at
    if answer.get("date"):
        try:
            day = dt.date.fromisoformat(str(answer["date"]))
        except ValueError:
            raise Rejected("date is not a date") from None
        if abs((day - sent_at.astimezone(IST).date()).days) > 7:
            raise Rejected("date is more than 7 days from the message")
        if day != sent_at.astimezone(IST).date():
            occurred = dt.datetime.combine(day, dt.time(12, 0), tzinfo=IST)
    reference = str(answer.get("reference") or "")
    return {
        "amount_paise": amount, "direction": answer["direction"], "account_last4": digits,
        "occurred_at": occurred.isoformat(), "counterparty": str(answer.get("counterparty") or "")[:200],
        "reference": reference[:64] if reference and _digits(reference) in _digits(original) else "",
    }


def suggest(raw):
    masked, mapping = masking.mask(raw.body, names=providers.is_cloud())
    answer = providers.ask(SYSTEM, masked)
    if isinstance(answer, dict):
        answer = {k: masking.unmask(v, mapping) for k, v in answer.items()}
    return check(answer, raw.body, raw.sent_at)
