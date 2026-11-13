"""SBI Card monthly statement. Written from the owner's real statements, 2026-11-13.
The statement shows only the last two card digits; credit limits are never read (rule 8)."""
import datetime as dt
import re

from .common import MONEY, Line, Statement, StatementError, paise

ROW = re.compile(rf"^(\d{{2}} [A-Z][a-z]{{2}} \d{{2}}) (.+?) ({MONEY}) ([DC])$")
# GST on a fee is printed on its own line, without a date, under the fee it belongs to.
TAX_ROW = re.compile(rf"^([IS]?[CGS]?GST DB @ [\d.]+%) ({MONEY}) ([DC])$")
ROUNDING_PAISE = 100  # SBI Card rounds the total outstanding; differences under Rs 1 are rounding
PERIOD = re.compile(r"for Statement Period: (\d{2} [A-Z][a-z]{2} \d{2}) to (\d{2} [A-Z][a-z]{2} \d{2})")
CARD = re.compile(r"XXXX XXXX XXXX XX(\d{2})")
DUE_DATE = re.compile(r"Payment Due Date\s*\n?.*?(\d{2} [A-Z][a-z]{2} \d{4})\s*$", re.M)
SUMMARY = re.compile(rf"Interest Charges\( ` \) \( ` \)\s*\n\s*({MONEY}) ({MONEY}) ({MONEY}) ({MONEY}) ({MONEY})")


def MATCH(pages):
    return "for Statement Period:" in pages[0] and "SBI Card" in pages[0]


def parse(pages):
    first = pages[0]
    period, card, summary = PERIOD.search(first), CARD.search(first), SUMMARY.search(first)
    if not (period and card and summary):
        raise StatementError("SBI Card: period, card digits or account summary not found")
    lines, last_date = [], None
    for raw in "\n".join(pages).splitlines():
        line = raw.strip()
        m = ROW.match(line)
        if m:
            last_date = dt.datetime.strptime(m.group(1), "%d %b %y").date()
            lines.append(Line(last_date, m.group(2)[:200], paise(m.group(3)), "debit" if m.group(4) == "D" else "credit"))
            continue
        tax = TAX_ROW.match(line)
        if tax and last_date:
            lines.append(Line(last_date, tax.group(1), paise(tax.group(2)), "debit" if tax.group(3) == "D" else "credit"))
    due = DUE_DATE.search(first)
    previous, credits, debits, fees, total = (paise(summary.group(i)) for i in range(1, 6))
    if abs(previous - credits + debits + fees - total) >= ROUNDING_PAISE:
        raise StatementError("SBI Card: account summary does not add up")
    rows_debit = sum(l.amount_paise for l in lines if l.direction == "debit")
    rows_credit = sum(l.amount_paise for l in lines if l.direction == "credit")
    if rows_debit != debits + fees or rows_credit != credits:
        raise StatementError("SBI Card: transaction rows do not match the account summary")
    return Statement(
        kind="card", account_digits=card.group(1),
        period_start=dt.datetime.strptime(period.group(1), "%d %b %y").date(),
        period_end=dt.datetime.strptime(period.group(2), "%d %b %y").date(),
        lines=lines, opening_paise=previous, closing_paise=total, total_due_paise=total,
        due_date=dt.datetime.strptime(due.group(1), "%d %b %Y").date() if due else None,
    )
