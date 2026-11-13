"""Mask a bank message before it goes to any model; put the real values back locally afterwards."""
import re

_VPA = re.compile(r"[\w.\-]+@[a-zA-Z][\w.\-]*")
_LONG = re.compile(r"(?<![\d,])\d{9,}(?![\d,])")  # references, phone and card numbers (amounts have , or .)
_NAME = re.compile(r"\b(?:[A-Z][a-zA-Z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-zA-Z]+|[A-Z]{2,})){1,3}\b")
_KEEP = {"HDFC", "ICICI", "SBI", "HSBC", "AXIS", "BANK", "CARD", "CREDIT", "DEBIT", "UPI", "IMPS", "NEFT", "RTGS",
         "NACH", "INR", "RS", "DEAR", "CUSTOMER", "ACCOUNT", "TRANSACTION", "ALERT", "INFO", "REF", "NOT", "YOU",
         "CALL", "SMS", "BLOCK", "AVL", "BAL", "LIMIT", "THANK"}


def mask(text, names=False):
    """Returns (masked text, {placeholder: original}). Names are masked only for cloud providers."""
    mapping = {}

    def sub(pattern, label, value):
        key = next((k for k, v in mapping.items() if v == value and k.startswith(f"<{label}")), None)
        if key is None:
            key = f"<{label}{sum(1 for k in mapping if k.startswith(f'<{label}')) + 1}>"
            mapping[key] = value
        return key

    out = _VPA.sub(lambda m: sub(_VPA, "VPA", m.group()), text)
    out = _LONG.sub(lambda m: sub(_LONG, "REF", m.group()), out)
    if names:
        def name(m):
            words = m.group().split()
            if all(w.upper().strip(".") in _KEEP for w in words):
                return m.group()
            return sub(_NAME, "NAME", m.group())
        out = _NAME.sub(name, out)
    return out, mapping


def unmask(value, mapping):
    if not isinstance(value, str):
        return value
    for key, original in mapping.items():
        value = value.replace(key, original)
    return value
