"""ICICI Bank savings account statement. Written from the owner's real statements, 2026-11-13."""
import datetime as dt
import re

from .common import MONEY, Statement, StatementError, balance_chain, last_digits, paise

DATE = re.compile(r"^(\d{2}-\d{2}-\d{4})\s*(.*)$")
ROW_END = re.compile(rf"^(.*?)\s*({MONEY})\s+({MONEY})\s*$")
HEADER = re.compile(r"Statement of Transactions in Savings Account (X+\d{4}) in INR for the period (\w+ \d{1,2}, \d{4}) - (\w+ \d{1,2}, \d{4})")


def MATCH(pages):
    return bool(HEADER.search("\n".join(pages)))


def parse(pages):
    text = "\n".join(pages)
    head = HEADER.search(text)
    start = dt.datetime.strptime(head.group(2), "%B %d, %Y").date()
    end = dt.datetime.strptime(head.group(3), "%B %d, %Y").date()
    section = text[head.end():]
    date, opening, rows, buffer = None, None, [], []
    for raw in section.splitlines():
        line = raw.strip()
        if line.startswith("Account Related Other Information"):
            break
        if line.startswith("Total:"):  # printed at the foot of every page
            buffer = []
            continue
        m = DATE.match(line)
        if m:
            date = dt.datetime.strptime(m.group(1), "%d-%m-%Y").date()
            line = m.group(2)
        if line.startswith("B/F"):
            opening = paise(re.findall(MONEY, line)[-1])
            buffer = []
            continue
        if opening is None:
            continue
        row = ROW_END.match(line)
        if row and date:
            buffer.append(row.group(1))
            rows.append((date, " ".join(buffer), paise(row.group(2)), paise(row.group(3))))
            buffer = []
        elif line:
            buffer.append(line)
    if opening is None:
        raise StatementError("ICICI: opening balance (B/F) not found")
    lines = balance_chain(rows, opening)
    return Statement(kind="bank", account_digits=last_digits(head.group(1)), period_start=start, period_end=end,
                     lines=lines, opening_paise=opening, closing_paise=lines[-1].balance_paise if lines else opening)
