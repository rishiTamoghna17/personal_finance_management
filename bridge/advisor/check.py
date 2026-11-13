"""The model may not invent money. Every rupee amount in an answer must be one of the facts it was given,
or the sum or difference of two of them (rounding to the rupee, or to 0.5% for "2.5 lakh" style, is allowed)."""
import re
from decimal import Decimal, InvalidOperation

NUM = r"([\d,]*\d(?:\.\d+)?)"
UNIT = r"(lakhs?|lacs?|crores?|cr|k)"
# "₹1,200", "Rs. 1200", "INR 1.2 lakh", "1,200 rupees", "2.5 lakh" (lakh/crore count as money even without ₹).
AMOUNT = re.compile(
    rf"(?:₹|\bRs\.?|\bINR)\s*{NUM}\s*{UNIT}?\b"
    rf"|\b{NUM}\s*(lakhs?|lacs?|crores?)\b"
    rf"|\b{NUM}\s*(?:rupees|rs\b)",
    re.IGNORECASE,
)
SCALE = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "crore": 10_000_000,
         "crores": 10_000_000, "cr": 10_000_000, "k": 1_000}


def amounts_in(text):
    """Rupee amounts written in the answer, as paise."""
    found = []
    for m in AMOUNT.finditer(text or ""):
        if m.group(1):
            number, unit = m.group(1), m.group(2)
        elif m.group(3):
            number, unit = m.group(3), m.group(4)
        else:
            number, unit = m.group(5), None
        try:
            value = Decimal(number.replace(",", ""))
        except (InvalidOperation, AttributeError):
            continue
        value *= SCALE.get((unit or "").lower(), 1)
        found.append(int(value * 100))
    return found


def allowed(facts):
    base = {v for v in facts if v}
    combos = set(base)
    values = sorted(base)
    for i, a in enumerate(values):
        for b in values[i:]:
            combos.add(a + b)
            combos.add(abs(a - b))
    return combos


def unsupported(answer, fact_amounts):
    """Amounts in the answer that no fact supports (empty list = the answer is fine)."""
    ok = allowed(fact_amounts)
    bad = []
    for paise in amounts_in(answer):
        if paise == 0:
            continue
        tolerance = max(100, paise // 200)
        if not any(abs(paise - v) <= tolerance for v in ok):
            bad.append(paise)
    return bad
