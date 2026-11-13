import base64
import datetime as dt
import json

import pytest

from core.crypto import CryptoError, decrypt, encrypt
from ingest.models import DropTally, LedgerEntry, RawMessage
from mail import tasks
from mail.models import GmailAccount, StatementAttachment
from mail.text import html_to_text, message_parts

pytestmark = pytest.mark.django_db
B64 = lambda s: base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")
NOV = int(dt.datetime(2026, 11, 2, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30))).timestamp() * 1000)

HDFC_DEBIT = ("HDFC BANK --> Dear Customer, Greetings from HDFC Bank! Rs.45.00 is debited from your account ending 1111 "
              "towards VPA abcd@ybl (NAME SURNAME) on 02-11-26. UPI transaction reference no.: 100000000301. "
              "If you did not authorize this transaction, please report it.")


def message(mid, subject, text, sender="HDFC Bank InstaAlerts <alerts@hdfcbank.bank.in>", html=False, pdf=None, when=NOV):
    part = {"mimeType": "text/html" if html else "text/plain", "body": {"data": B64(text)}}
    parts = [part]
    if pdf:
        parts.append({"mimeType": "application/pdf", "filename": pdf, "body": {"attachmentId": "att-" + mid, "size": 1234}})
    return {"id": mid, "internalDate": str(when), "payload": {
        "headers": [{"name": "From", "value": sender}, {"name": "Subject", "value": subject}],
        "mimeType": "multipart/mixed", "parts": parts}}


@pytest.fixture
def account():
    return GmailAccount.objects.create(tag="acct1", token_encrypted=encrypt(json.dumps({"refresh_token": "x"})))


def test_encryption_round_trip_and_wrong_key(settings):
    token = encrypt("secret value")
    assert "secret value" not in token and decrypt(token) == "secret value"
    settings.BRIDGE_ENCRYPTION_KEY = "Sxl2B7oVJ7bq3cR0dFQhC9mWm7bP0xYk8dV2nH5u4tA="
    with pytest.raises(CryptoError):
        decrypt(token)


def test_message_parts_prefers_plain_and_lists_pdfs():
    sender, subject, text, pdfs = message_parts(message("m1", "Statement", "hello   world", pdf="Statement.pdf"))
    assert (sender, subject, text) == ("HDFC Bank InstaAlerts <alerts@hdfcbank.bank.in>", "Statement", "hello world")
    assert pdfs == [{"filename": "Statement.pdf", "attachment_id": "att-m1", "size": 1234}]


def test_html_to_text():
    assert " ".join(html_to_text("<html><style>x{}</style><p>Rs.45&nbsp;debited</p><br>ok</html>").split()) == "Rs.45 debited ok"


def test_bank_query_lists_only_profile_domains():
    query = tasks.bank_query(1700000000)
    assert query.startswith("after:1700000000 from:(") and "hdfcbank.bank.in" in query and "sbicard.com" in query


def test_otp_email_is_dropped_before_storage(account, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        result = tasks.ingest_message(account, message("m1", "One Time Password (OTP) for your online transaction", "482913 is your OTP."))
    assert result == "dropped" and callbacks == []
    assert RawMessage.objects.count() == 0
    assert DropTally.objects.get().header == "HDFCBANK.BANK.IN"


def test_alert_email_becomes_a_transaction_once(account, firefly, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.ingest_message(account, message("m2", "You have done a UPI txn", HDFC_DEBIT)) == "stored"
    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.ingest_message(account, message("m2", "You have done a UPI txn", HDFC_DEBIT)) == "duplicate"
    raw = RawMessage.objects.get()
    assert (raw.source, raw.header, raw.status, raw.pattern_ref) == ("email", "HDFCBANK.BANK.IN", "parsed", "hdfc-email/upi-debit")
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.amount_paise, entry.reference) == ("withdrawal", 4500, "100000000301")


def test_email_and_sms_for_one_payment_are_one_transaction(account, firefly, settings, django_capture_on_commit_callbacks):
    from tests.ingest.helpers import post_sms

    settings.INGEST_PROFILE_DIRS = [settings.BASE_DIR / "ingest" / "profiles"]
    from ingest import parser
    parser.clear_cache()
    sms = "Sent Rs.45.00 From HDFC Bank A/C *1111 To NAME SURNAME On 02/11/26 Ref 100000000301 Not You? Call 18002586161"
    with django_capture_on_commit_callbacks(execute=True):
        post_sms("JM-HDFCBK-S", sms)
    with django_capture_on_commit_callbacks(execute=True):
        tasks.ingest_message(account, message("m3", "You have done a UPI txn", HDFC_DEBIT))
    assert RawMessage.objects.count() == 2
    entry = LedgerEntry.objects.get()
    assert entry.messages.count() == 2  # same UPI reference -> same payment


def test_notice_email_is_ignored_with_reason(account, firefly, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        tasks.ingest_message(account, message("m4", "Maintenance on 14 Nov", "<p>Net banking will be down for 4 hours.</p>", html=True))
    raw = RawMessage.objects.get()
    assert (raw.status, raw.status_reason) == ("ignored", "bank email without a transaction (notice or offer)")


def test_statement_pdf_is_recorded_for_the_statement_import(account, firefly, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        tasks.ingest_message(account, message("m5", "Statements for Accounts under Customer ID 000-XXXXXX",
                                              "This statement is secured by a unique password.",
                                              sender="HSBC <statements@notification.hsbc.bank.in>", pdf="01NOV2026.pdf"))
    att = StatementAttachment.objects.get()
    assert (att.filename, att.status, att.account, att.raw.status) == ("01NOV2026.pdf", "pending", account, "ignored")


def test_poll_reads_oldest_first_and_remembers_where_it_stopped(account, firefly, monkeypatch, django_capture_on_commit_callbacks):
    msgs = {"a": message("a", "UPI", HDFC_DEBIT.replace("100000000301", "100000000401"), when=NOV),
            "b": message("b", "UPI", HDFC_DEBIT.replace("100000000301", "100000000402"), when=NOV + 60000)}
    seen_queries = []
    monkeypatch.setattr(tasks.gmail, "service_for", lambda acct: object())
    monkeypatch.setattr(tasks.gmail, "list_ids", lambda service, q: seen_queries.append(q) or ["b", "a"])
    monkeypatch.setattr(tasks.gmail, "get_message", lambda service, mid: msgs[mid])
    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.poll_account(account.pk) == {"stored": 2, "dropped": 0, "duplicate": 0, "other_sender": 0}
    account.refresh_from_db()
    assert account.last_seen_ms == NOV + 60000
    assert seen_queries[0].startswith("after:1793471400 ")  # ledger start, 2026-11-01 IST
    with django_capture_on_commit_callbacks(execute=True):
        assert tasks.poll_account(account.pk) == {"stored": 0, "dropped": 0, "duplicate": 2, "other_sender": 0}
    assert seen_queries[1].startswith(f"after:{(NOV + 60000) // 1000} ")


def test_marketing_sub_domain_is_not_stored(account, firefly):
    msg = message("m9", "Festive offer", "Get cashback", sender="HDFC Bank <information@mailers.hdfcbank.bank.in>")
    assert tasks.ingest_message(account, msg) == "other_sender"
    assert RawMessage.objects.count() == 0


def test_long_numbers_in_attachment_names_are_masked():
    from mail.text import safe_filename

    assert safe_filename("4400123456789012_17102026.pdf") == "XXXXXXXXXXXX9012_17102026.pdf"
    assert safe_filename("Statement_2026MTH08_123456789.pdf") == "Statement_2026MTH08_XXXXX6789.pdf"
    assert safe_filename("29OCT2026.pdf") == "29OCT2026.pdf"
