"""Axis Bank credit card "EMI Letter with Monthly EMI Details". Written from the owner's real letter, 2026-11-14.
The amortisation table on the last page is the source of truth; its principal column must add up to the
converted amount (within the table's whole-rupee rounding), otherwise the letter is refused."""
import datetime as dt
import re

from core.money import to_paise

from .common import EmiLetter, Instalment, StatementError, last_digits

CARD = re.compile(r"Card number : (\d{4}X+\d{4})")
AMOUNT = re.compile(r"Transaction Amount : Rs\. ([\d,]+(?:\.\d{1,2})?)")
MERCHANT = re.compile(r"Merchant Name : (.+)")
RATE = re.compile(r"Interest Rate : ([\d.]+ ?% ?p\.?[ma]\.?)")
REF = re.compile(r"Ref\. ?No\.? ?:? ?([A-Z]+_\w+)", re.IGNORECASE)
# "<loan id> 1 13-NOV-26 3507 3207 300 <outstanding> 09-OCT-26"
ROW = re.compile(r"^\S+ (\d{1,3}) (\d{2}-[A-Z]{3}-\d{2}) (\d+(?:\.\d{1,2})?) (\d+(?:\.\d{1,2})?) (\d+(?:\.\d{1,2})?) \S+ \d{2}-[A-Z]{3}-\d{2}$")


def MATCH(pages):
    return "Conversion of Transaction into EMI" in pages[0] and "AXIS" in pages[0].upper()


def _rupees(text):
    return to_paise(text.replace(",", ""))


def parse(pages):
    first = pages[0]
    card, amount, merchant, rate, ref = (rx.search(first) for rx in (CARD, AMOUNT, MERCHANT, RATE, REF))
    if not (card and amount and merchant):
        raise StatementError("Axis EMI letter: card, amount or merchant not found")
    instalments = []
    for raw in "\n".join(pages).splitlines():
        m = ROW.match(raw.strip())
        if m:
            number = int(m.group(1))
            instalments.append(Instalment(number, dt.datetime.strptime(m.group(2).title(), "%d-%b-%y").date(),
                                          _rupees(m.group(3)), _rupees(m.group(4)), _rupees(m.group(5))))
    principal = _rupees(amount.group(1))
    # The table is printed in whole rupees, so each row may be up to Rs 1 off (seen: Rs 1 on a 6-month plan).
    if not instalments or abs(sum(i.principal_paise for i in instalments) - principal) > 100 * len(instalments):
        raise StatementError("Axis EMI letter: schedule principal does not add up to the converted amount")
    return EmiLetter(
        account_digits=last_digits(card.group(1)), reference_tail=(ref.group(1)[-4:] if ref else ""),
        merchant=" ".join(merchant.group(1).split())[:120], principal_paise=principal,
        rate_text=rate.group(1) if rate else "", instalments=instalments,
    )
