"""Axis Bank credit card statement. Written from the owner's real statements, 2026-11-13.
Credit limits are never read (rule 8)."""
import datetime as dt
import re

from .common import MONEY, Line, Statement, StatementError, last_digits, paise

ROW = re.compile(rf"^(\d{{2}}/\d{{2}}/\d{{4}}) (.+?) ({MONEY}) (Dr|Cr)$")
SUMMARY = re.compile(rf"({MONEY}) (Dr|Cr) ({MONEY}) (Dr|Cr) (\d{{2}}/\d{{2}}/\d{{4}}) - (\d{{2}}/\d{{2}}/\d{{4}}) (\d{{2}}/\d{{2}}/\d{{4}})")
CARD = re.compile(r"Card No: (\d+\*+\d{4})")
TOTALS = re.compile(rf"\n({MONEY}) ({MONEY}) ({MONEY}) ({MONEY}) ({MONEY}) ({MONEY}) ({MONEY}) (Dr|Cr)")


def MATCH(pages):
    return "Axis Bank" in pages[0] and "Credit Card Statement" in pages[0] and "PAYMENT SUMMARY" in pages[0]


def _d(text):
    return dt.datetime.strptime(text, "%d/%m/%Y").date()


def parse(pages):
    first = pages[0]
    summary, card = SUMMARY.search(first), CARD.search(first)
    if not (summary and card):
        raise StatementError("Axis: payment summary or card number not found")
    lines = []
    for raw in "\n".join(pages).splitlines():
        m = ROW.match(raw.strip())
        if m:
            lines.append(Line(_d(m.group(1)), m.group(2)[:200], paise(m.group(3)), "debit" if m.group(4) == "Dr" else "credit"))
    total = paise(summary.group(1)) * (1 if summary.group(2) == "Dr" else -1)
    totals = TOTALS.search(first)
    opening = None
    if totals:
        prev, payments, credits, purchase, cash, other, owed = (paise(totals.group(i)) for i in range(1, 8))
        owed *= 1 if totals.group(8) == "Dr" else -1
        if prev - payments - credits + purchase + cash + other != owed:
            raise StatementError("Axis: account summary does not add up")
        opening = prev
    return Statement(
        kind="card", account_digits=last_digits(card.group(1)), period_start=_d(summary.group(5)),
        period_end=_d(summary.group(6)), lines=lines, opening_paise=opening, closing_paise=total,
        total_due_paise=total, minimum_due_paise=paise(summary.group(3)), due_date=_d(summary.group(7)),
    )
