"""CDSL CAS reader, against text shaped like the owner's real CAS (2026-11-14). All names and values invented."""
import datetime as dt

import pytest

from statements.parsers import cdsl_cas
from statements.parsers.common import StatementError

PAGE0 = """CONSOLIDATED ACCOUNT STATEMENT (CAS) FOR SECURITIES HELD IN DEMAT
FORM AND INVESTMENTS IN MUTUAL FUNDS FOR THE PERIOD FROM 01-09-2026
TO 30-09-2026
CDSL Demat Accounts 1,110.00"""

HOLDINGS = """Market
Value
SOME POWER & GRID
LIMITED # NEW
INE000A01011 3.000 -- -- -- 3.000 100.0000 300.00
EQUITY SHARES OF RS. 1/-
AFTER SUB DIVISION
ABC AMC LTD#ABC MF-ABC SMALL CAP
INF000K01011 10.000 -- -- -- 10.000 50.5000 505.00
FUND-DIRECT PLAN-GROWTH
OPTION
XYZ AM PVT LTD#XYZ MF-XYZ
INF000K01029 MF-XYZ BHARAT 1.000 -- -- -- 1.000 205.0000 205.00
22 ETF
Portfolio Value ` 1,010.00 as on 30-09-2026
DP Name : SECOND BROKER LIMITED
Value
OTHER CEMENT LIMITED #
INE000B01012 1.000 -- -- -- 1.000 100.0000 100.00
EQUITY SHARES
Portfolio Value ` 100.00 as on 30-09-2026
Grand Total 1,110.00"""


def pages(holdings=HOLDINGS):
    return [PAGE0, holdings]


def test_reads_holdings_values_and_names():
    assert cdsl_cas.MATCH(pages())
    doc = cdsl_cas.parse(pages())
    assert doc.statement_date == dt.date(2026, 9, 30) and doc.total_paise == 111000
    assert [(h.kind, h.isin, h.units, h.price, h.value_paise) for h in doc.holdings] == [
        ("stock", "INE000A01011", "3.000", "100.0000", 30000),
        ("mutual_fund", "INF000K01011", "10.000", "50.5000", 50500),
        ("mutual_fund", "INF000K01029", "1.000", "205.0000", 20500),
        ("stock", "INE000B01012", "1.000", "100.0000", 10000),
    ]
    assert [h.name for h in doc.holdings] == [
        "SOME POWER & GRID LIMITED", "ABC MF-ABC SMALL CAP FUND-DIRECT PLAN-GROWTH OPTION",
        "XYZ MF-XYZ MF-XYZ BHARAT 22 ETF", "OTHER CEMENT LIMITED"]


@pytest.mark.parametrize("old,new", [
    ("10.000 50.5000 505.00", "10.000 50.5000 515.00"),  # units x price does not give the value
    ("Portfolio Value ` 1,010.00", "Portfolio Value ` 1,020.00"),  # account total wrong
    ("Grand Total 1,110.00", "Grand Total 1,111.00"),
    ("as on 30-09-2026\nDP", "as on 31-08-2026\nDP"),  # holdings from another date
])
def test_refuses_a_cas_that_does_not_add_up(old, new):
    with pytest.raises(StatementError):
        cdsl_cas.parse(pages(HOLDINGS.replace(old, new)))
