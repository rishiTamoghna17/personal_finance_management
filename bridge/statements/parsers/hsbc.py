"""HSBC India composite statement (savings). Written from the owner's real statements, 2026-11-13."""
import datetime as dt
import re

from .common import MONEY, Statement, StatementError, balance_chain, last_digits, paise

DATE = re.compile(r"^(\d{2}[A-Z][a-z]{2}\d{4})\s*(.*)$")
ROW_END = re.compile(rf"^(.*?)\s*({MONEY})\s+({MONEY})\s*$")
ACCOUNT = re.compile(r"SAVINGS ACCOUNT[-\w]*\s+(\d{3}-\d{6}-\d{3})")
STATEMENT_DATE = re.compile(r"Statement Date\s+(\d{2}[A-Z]{3}\d{4})")


def MATCH(pages):
    text = "\n".join(pages)
    return "Composite Statement" in text and "BALANCE BROUGHT FORWARD" in text


def parse(pages):
    text = "\n".join(pages)
    account = ACCOUNT.search(text)
    stmt_date = STATEMENT_DATE.search(text)
    if not account or not stmt_date:
        raise StatementError("HSBC: account number or statement date not found")
    date, opening, rows, buffer, start, closing = None, None, [], [], None, None
    for raw in text.splitlines():
        line = raw.strip()
        m = DATE.match(line)
        if m:
            date = dt.datetime.strptime(m.group(1), "%d%b%Y").date()
            line = m.group(2)
        if "BALANCE BROUGHT FORWARD" in line:
            if opening is None:  # later pages repeat it after each page break
                opening = paise(re.findall(MONEY, line)[-1])
                start = date
            buffer = []
            continue
        if "BALANCE CARRIED FORWARD" in line:
            buffer = []
            continue
        if line.startswith("CLOSING BALANCE"):
            closing = paise(re.findall(MONEY, line)[-1])
            break
        if opening is None:
            continue
        end = ROW_END.match(line)
        if end and date:
            buffer.append(end.group(1))
            rows.append((date, " ".join(buffer), paise(end.group(2)), paise(end.group(3))))
            buffer = []
        elif line:
            buffer.append(line)
    if opening is None:
        raise StatementError("HSBC: opening balance not found")
    lines = balance_chain(rows, opening)
    last = lines[-1].balance_paise if lines else opening
    if closing is not None and closing != last:
        raise StatementError("HSBC: closing balance does not match the transactions")
    return Statement(
        kind="bank", account_digits=last_digits(account.group(1)), period_start=start,
        period_end=dt.datetime.strptime(stmt_date.group(1).title(), "%d%b%Y").date(),
        lines=lines, opening_paise=opening, closing_paise=lines[-1].balance_paise if lines else opening,
    )
