"""Statement parsers against text shaped like the owner's real statements (all values invented)."""
import datetime as dt

import pytest

from statements.parsers import axis_card, hsbc, icici, sbi_card
from statements.parsers.common import StatementError

HSBC = """Composite Statement
Statement Date 29OCT2026
Savings Account INR 000-000000-006 201.37 201.37
Details of Your Accounts
SAVINGS ACCOUNT-RES 000-000000-006
Date Transaction Details Deposits Withdrawals Balance
29Sep2026 BALANCE BROUGHT FORWARD 64.34
01Oct2026 EMPLOYER
MONTHSAL
EMPLOYER PRIVATE LIMI 48,000.00 48,064.34
UPI10000000000000001
100000000001
SHOP NAME 64.00 48,000.34
BALANCE CARRIED FORWARD 48,000.34
Page 2
BALANCE BROUGHT FORWARD 48,000.34
05Oct2026 UPI10000000000000002
100000000002
abcd@okicici 47,798.97 201.37
CLOSING BALANCE 201.37
Transaction Turnover 48,000.00 47,862.97"""

ICICI = """Statement of Transactions in Savings Account XXXXXXXX7378 in INR for the period June 01, 2026 - June 30, 2026
DATE MODE PARTICULARS DEPOSITS WITHDRAWALS BALANCE
01-06-2026 B/F 14.57
03-06-2026 NEFT-EMPLOYER 49,800.00 49,814.57
03-06-2026 UPI/SHOP/shop@ybl/UPI/YES BANK 1,000.00 48,814.57
Total: 49,800.00 1,000.00 48,814.57
Page 1 of 2
30-06-2026 MMT/IMPS/100000000003/Payout 9.00 48,823.57
Total: 9.00 0.00 48,823.57
Account Related Other Information"""

SBI = """TAMOGHNA Credit Card Number
XXXX XXXX XXXX XX73
Payment Due Date
05 Jun 2026
ACCOUNT SUMMARY
Previous Balance Reversals & other Purchases & Other Fee, Taxes & Total Outstanding
( ` ) Credits ( ` ) Debits ( ` ) Interest Charges( ` ) ( ` )
5,128.91 6,133.84 4,090.47 20.60 3,106.00
for Statement Period: 18 Apr 26 to 17 May 26 SBI Card
02 May 26 PAYMENT RECEIVED 6,133.84 C
03 May 26 AMAZON MUMBAI MAH 4,090.47 D
05 May 26 LATE FEE 17.46 D
IGST DB @ 18.00% 3.14 D"""

AXIS = """Axis Bank Amex Privilege Credit Card Statement
PAYMENT SUMMARY
99.00 Dr 99.00 Dr 15/09/2026 - 10/11/2026 30/11/2026 10/11/2026
Card No: 123456*****9315 Name NAME
14/10/2026 SHOP ONLINE,BANGALORE CLOTH STORES 2,568.00 Dr
20/10/2026 SHOP ONLINE,BANGALORE CLOTH STORES 2,469.00 Cr"""


def test_hsbc_follows_the_running_balance_across_pages():
    s = hsbc.parse([HSBC])
    assert (s.kind, s.account_digits, s.period_end, s.opening_paise, s.closing_paise) == ("bank", "0006", dt.date(2026, 10, 29), 6434, 20137)
    assert [(l.direction, l.amount_paise) for l in s.lines] == [("credit", 4800000), ("debit", 6400), ("debit", 4779897)]
    assert s.lines[1].reference == "100000000001"


def test_hsbc_refuses_a_statement_that_does_not_add_up():
    with pytest.raises(StatementError):
        hsbc.parse([HSBC.replace("48,000.34\nBALANCE CARRIED", "48,000.35\nBALANCE CARRIED")])


def test_icici_reads_every_page_and_skips_page_totals():
    s = icici.parse([ICICI])
    assert (s.account_digits, s.period_start, s.period_end, s.closing_paise) == ("7378", dt.date(2026, 6, 1), dt.date(2026, 6, 30), 4882357)
    assert len(s.lines) == 3 and s.lines[2].reference == "100000000003"


def test_sbi_card_reads_undated_gst_rows_and_tolerates_rounding():
    s = sbi_card.parse([SBI])
    assert (s.kind, s.account_digits, s.closing_paise, s.due_date) == ("card", "73", 310600, dt.date(2026, 6, 5))
    assert [l.description for l in s.lines][-1] == "IGST DB @ 18.00%"
    assert sum(l.amount_paise for l in s.lines if l.direction == "debit") == 409047 + 2060


def test_sbi_card_refuses_rows_that_do_not_match_the_summary():
    with pytest.raises(StatementError):
        sbi_card.parse([SBI.replace("IGST DB @ 18.00% 3.14 D", "")])


def test_axis_card():
    s = axis_card.parse([AXIS])
    assert (s.account_digits, s.closing_paise, s.minimum_due_paise, s.due_date) == ("9315", 9900, 9900, dt.date(2026, 11, 30))
    assert [(l.direction, l.amount_paise) for l in s.lines] == [("debit", 256800), ("credit", 246900)]


def test_parsers_only_claim_their_own_layout():
    assert hsbc.MATCH([HSBC]) and not icici.MATCH([HSBC]) and not sbi_card.MATCH([HSBC]) and not axis_card.MATCH([HSBC])
