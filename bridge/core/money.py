"""Money helpers. Integer paise inside the bridge, decimal strings to Firefly.

Floats are rejected everywhere: a float has already lost precision by the
time it reaches us, so accepting one would hide the error.
"""
from decimal import Decimal, InvalidOperation

PAISE_PER_RUPEE = 100


class MoneyError(ValueError):
    pass


def to_paise(amount):
    """Convert a rupee amount (str, int or Decimal) to integer paise.

    Accepts Indian grouping ("1,23,456.78") and a leading sign. Raises
    MoneyError for floats, non-numbers, and anything finer than one paisa.
    Trailing zeros beyond two places ("12.500000") are fine: Firefly returns those.
    """
    if isinstance(amount, bool) or isinstance(amount, float):
        raise MoneyError(f"refusing {type(amount).__name__} as money; pass a string, int or Decimal")
    if isinstance(amount, int):
        return amount * PAISE_PER_RUPEE
    if isinstance(amount, str):
        text = amount.strip().replace(",", "")
        if not text:
            raise MoneyError("empty amount")
        try:
            amount = Decimal(text)
        except InvalidOperation:
            raise MoneyError("not a number") from None
    if not isinstance(amount, Decimal):
        raise MoneyError(f"unsupported money type {type(amount).__name__}")
    if not amount.is_finite():
        raise MoneyError("amount is not finite")
    paise = amount * PAISE_PER_RUPEE
    if paise != paise.to_integral_value():
        raise MoneyError("amount is finer than one paisa")
    return int(paise)


def to_decimal_string(paise):
    """Integer paise -> "1234.50", the form the Firefly API takes."""
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise MoneyError("paise must be an int")
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(paise), PAISE_PER_RUPEE)
    return f"{sign}{rupees}.{rem:02d}"


def format_inr(paise):
    """Integer paise -> "₹12,34,567.89" with lakh/crore grouping."""
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise MoneyError("paise must be an int")
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(paise), PAISE_PER_RUPEE)
    digits = str(rupees)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    groups.append(tail)
    return f"{sign}₹{','.join(groups)}.{rem:02d}"
