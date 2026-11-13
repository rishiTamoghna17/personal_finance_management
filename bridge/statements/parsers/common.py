"""Shared pieces for statement parsers. Money is integer paise; nothing here touches floats."""
import datetime as dt
import re
from dataclasses import dataclass, field

from core.money import to_paise

MONEY = r"\d{1,3}(?:,\d{2,3})*\.\d{2}"
MONEY_RE = re.compile(MONEY)
REF_RE = re.compile(r"(?<!\d)(\d{12})(?!\d)")  # UPI RRN / IMPS reference


class StatementError(ValueError):
    pass


@dataclass
class Line:
    date: dt.date
    description: str
    amount_paise: int
    direction: str  # debit | credit
    reference: str = ""
    balance_paise: int | None = None


@dataclass
class Statement:
    kind: str  # bank | card
    account_digits: str  # last 4, or fewer when the statement shows fewer
    period_start: dt.date | None
    period_end: dt.date
    lines: list = field(default_factory=list)
    opening_paise: int | None = None
    closing_paise: int | None = None  # bank: money in the account; card: amount owed
    total_due_paise: int | None = None
    minimum_due_paise: int | None = None
    due_date: dt.date | None = None


def paise(text):
    return to_paise(text.replace(",", ""))


def last_digits(text, keep=4):
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[-keep:]


def balance_chain(rows, opening):
    """rows: [(date, description, amount_paise, balance_paise)]. Direction comes from the balance moving;
    a row that fits neither way means the text was misread, so the whole statement is refused."""
    lines, previous = [], opening
    for date, description, amount, balance in rows:
        if previous + amount == balance:
            direction = "credit"
        elif previous - amount == balance:
            direction = "debit"
        else:
            raise StatementError(f"balance does not add up on {date:%d %b %Y}")
        ref = REF_RE.search(description)
        lines.append(Line(date, " ".join(description.split())[:200], amount, direction, ref.group(1) if ref else "", balance))
        previous = balance
    return lines
