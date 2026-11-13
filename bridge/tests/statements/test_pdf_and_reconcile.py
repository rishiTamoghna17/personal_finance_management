import datetime as dt
import os

import pikepdf
import pytest

from ingest.models import BalanceObservation, LedgerEntry, RawMessage, ReviewItem
from statements import pdf
from statements.parsers.common import Line, Statement
from statements.reconcile import apply_statement
from tests.ingest.helpers import ingest

pytestmark = pytest.mark.django_db


def test_unlock_in_memory_only(tmp_path):
    path = tmp_path / "locked.pdf"
    doc = pikepdf.new()
    doc.add_blank_page()
    doc.save(path, encryption=pikepdf.Encryption(owner="owner-pw", user="right-pw", R=6))
    before = sorted(os.listdir(tmp_path))
    with pytest.raises(pdf.PdfError):
        pdf.unlock(path, ["wrong"])
    index, pages = pdf.unlock(path, ["wrong", "right-pw"])
    assert index == 1 and len(pages) == 1
    assert sorted(os.listdir(tmp_path)) == before  # no unlocked copy written


class Att:
    def __init__(self, pk, key):
        self.pk, self.key = pk, key


def bank_statement(lines, closing=500000):
    return Statement(kind="bank", account_digits="1111", period_start=dt.date(2026, 11, 1), period_end=dt.date(2026, 11, 30),
                     lines=lines, opening_paise=0, closing_paise=closing)


def test_statement_line_matches_the_sms_payment(firefly, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: INR 500.00 debited from a/c XX1111 to shop@upi on 12-11-26 ref 111111111111")
    result = apply_statement(Att(1, "hsbc"), bank_statement([Line(dt.date(2026, 11, 13), "UPI shop", 50000, "debit")]))
    assert "matched 1" in result
    entry = LedgerEntry.objects.get()
    assert entry.messages.count() == 2 and entry.messages.filter(raw__source="pdf").count() == 1


def test_line_missed_by_sms_and_email_becomes_a_new_transaction(firefly):
    result = apply_statement(Att(2, "hsbc"), bank_statement([Line(dt.date(2026, 11, 20), "BANK CHARGES", 11800, "debit")]))
    assert "added 1" in result
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.amount_paise, entry.source_account_id) == ("withdrawal", 11800, "1")


def test_lines_before_the_ledger_start_are_not_posted(firefly):
    result = apply_statement(Att(3, "hsbc"), bank_statement([Line(dt.date(2026, 10, 20), "OLD", 100, "debit")]))
    assert "before_start 1" in result and LedgerEntry.objects.count() == 0


def test_closing_balance_is_confirmed_and_card_balance_is_negative(firefly):
    apply_statement(Att(4, "hsbc"), bank_statement([], closing=20137))
    card = Statement(kind="card", account_digits="99", period_start=None, period_end=dt.date(2026, 11, 10), closing_paise=9900)
    apply_statement(Att(5, "axis-card"), card)
    assert sorted(BalanceObservation.objects.values_list("firefly_account_id", "balance_paise")) == [("1", 20137), ("3", -9900)]


def test_applying_the_same_statement_twice_changes_nothing(firefly):
    st = bank_statement([Line(dt.date(2026, 11, 20), "BANK CHARGES", 11800, "debit")])
    apply_statement(Att(6, "hsbc"), st)
    apply_statement(Att(6, "hsbc"), st)
    assert LedgerEntry.objects.count() == 1 and BalanceObservation.objects.count() == 1


def test_unknown_account_goes_to_review(firefly):
    st = bank_statement([])
    st.account_digits = "5555"
    assert "account not found" in apply_statement(Att(7, "hsbc"), st)
    assert ReviewItem.objects.get().reason == "unknown_account"
