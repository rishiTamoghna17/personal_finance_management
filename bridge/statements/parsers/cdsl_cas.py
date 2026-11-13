"""CDSL Consolidated Account Statement (CAS). Written from the owner's real statements, 2026-11-14.
Reads the holdings tables ("ISIN ... current balance ... market price ... value"). Values are exactly as the CAS
states them (rule 9). Refused unless every row's units x price matches its value, every demat account adds up to
its "Portfolio Value", and the accounts add up to the "Grand Total"."""
import datetime as dt
import re
from decimal import Decimal

from .common import CasDocument, Holding, StatementError, paise

NUM = r"[\d,]+"
ROW = re.compile(rf"^(IN[EF][0-9A-Z]{{9}}) ?(.*?) ?({NUM}\.\d{{3}}) (?:\S+ ){{3}}({NUM}\.\d{{3}}) ({NUM}\.\d{{4}}) ({NUM}\.\d{{2}})$")
ACCOUNT_TOTAL = re.compile(rf"Portfolio Value ` ({NUM}\.\d{{2}}) as on (\d{{2}}-\d{{2}}-\d{{4}})")
GRAND = re.compile(rf"Grand Total ({NUM}\.\d{{2}})")
PERIOD_END = re.compile(r"\bTO (\d{2}-\d{2}-\d{4})")
NAME_LINE = re.compile(r"^[A-Z0-9&.,()#/' -]+$")  # English name lines only; the Hindi layer is skipped


def MATCH(pages):
    return "CONSOLIDATED ACCOUNT STATEMENT (CAS)" in pages[0] and "Demat" in pages[0]


def _d(text):
    return dt.datetime.strptime(text, "%d-%m-%Y").date()


# A holding's name is printed around its row: lines before it, text inside the row, and lines after it ending
# with one of these words (e.g. "FUND-DIRECT PLAN-GROWTH", "AFTER SUB DIVISION", "22 ETF").
NAME_END = re.compile(r"(GROWTH|OPTION|DIVISION|SHARES|ETF|IDCW|DIVIDEND|BONUS)$")


def _short_name(isin, parts):
    """Stocks: the company (before '#'); funds: the scheme (after '#')."""
    text = " ".join(" ".join(parts).split())
    if "#" in text:
        company, scheme = (t.strip() for t in text.split("#", 1))
        text = scheme if isin.startswith("INF") and scheme else company
    return text[:200] or isin


def parse(pages):
    text = "\n".join(pages)
    grand, end = GRAND.search(text), PERIOD_END.search(pages[0])
    if not (grand and end):
        raise StatementError("CDSL CAS: grand total or statement period not found")
    statement_date = _d(end.group(1))
    tokens = []  # ("row", match) | ("name", text) | ("total", match) | ("break", None)
    for raw in text.splitlines():
        line = raw.strip()
        row, total = ROW.match(line), ACCOUNT_TOTAL.match(line)
        if row:
            tokens.append(("row", row))
        elif total:
            tokens.append(("total", total))
        elif line in ("Value", "Market") or line.startswith(("STATEMENT", "Page ", "DP Name")):
            tokens.append(("break", None))
        elif NAME_LINE.match(line) and len(line) > 2:
            tokens.append(("name", line))
        else:
            tokens.append(("break", None))

    holdings, section, pending = [], [], []
    for i, (kind, item) in enumerate(tokens):
        if kind == "name":
            pending.append(item)
        elif kind == "break":
            pending = []
        elif kind == "row":
            isin, middle, _, units, price, value = item.groups()
            if abs(Decimal(units.replace(",", "")) * Decimal(price.replace(",", "")) - Decimal(value.replace(",", ""))) > 1:
                raise StatementError(f"CDSL CAS: units x price does not match the value for {isin}")
            after = []
            for later_kind, later in tokens[i + 1:]:
                if later_kind != "name":
                    break
                after.append(later)
                if NAME_END.search(later):
                    break
            if after and NAME_END.search(after[-1]):
                # A lone "OPTION" line also belongs to this name ("...PLAN-GROWTH" / "OPTION").
                nxt = tokens[i + 1 + len(after)] if i + 1 + len(after) < len(tokens) else ("", "")
                if nxt == ("name", "OPTION"):
                    after.append("OPTION")
                consumed = len(after)
            else:
                after, consumed = [], 0
            holding = Holding("mutual_fund" if isin.startswith("INF") else "stock", isin,
                              _short_name(isin, pending + ([middle] if middle else []) + after),
                              units.replace(",", ""), price.replace(",", ""), paise(value))
            holdings.append(holding)
            section.append(holding)
            pending = []
            for j in range(i + 1, i + 1 + consumed):
                tokens[j] = ("used", None)
        elif kind == "total":
            if _d(item.group(2)) != statement_date:
                raise StatementError("CDSL CAS: holdings dated differently from the statement period")
            if sum(h.value_paise for h in section) != paise(item.group(1)):
                raise StatementError("CDSL CAS: a demat account's holdings do not add up to its portfolio value")
            section, pending = [], []
    if section:
        raise StatementError("CDSL CAS: holdings found after the last portfolio value line")
    total_paise = paise(grand.group(1))
    if sum(h.value_paise for h in holdings) != total_paise:
        raise StatementError("CDSL CAS: holdings do not add up to the grand total")
    return CasDocument(statement_date=statement_date, holdings=holdings, total_paise=total_paise)
