import datetime as dt

import pytest

from ingest import parser
from ingest.parser import ProfileError, header_of, parse

from .helpers import BASE


@pytest.mark.parametrize(
    "sender,header",
    [("VM-TESTBK", "TESTBK"), ("JD-TESTBK-S", "TESTBK"), ("ad-testbk-t", "TESTBK"), ("+919800000000", "+919800000000"), ("TESTBK", "TESTBK")],
)
def test_header_of(sender, header):
    assert header_of(sender) == header


def test_upi_debit_with_balance():
    r = parse("TESTBK", "TESTBANK: INR 1,23,456.78 debited from a/c XX1111 to shop@upi on 12-11-26 ref 123456789012. Bal INR 9,999.00", BASE)
    assert r.status == "parsed"
    p = r.parsed
    assert (p.amount_paise, p.direction, p.channel, p.account_last4) == (12345678, "debit", "upi", "1111")
    assert (p.vpa, p.reference, p.balance_paise, p.occurred_at) == ("shop@upi", "123456789012", 999900, BASE)


def test_late_sms_uses_the_date_in_the_message():
    r = parse("TESTBK", "TESTBANK: INR 10.00 debited from a/c XX1111 to a@b on 09-11-26 ref 123456789012", BASE)
    assert r.parsed.occurred_at.date() == dt.date(2026, 11, 9)


def test_whitespace_is_normalised():
    r = parse("TESTBK", "TESTBANK:   INR 10.00\ndebited from a/c XX1111 to a@b on 12-11-26 ref 123456789012", BASE)
    assert r.status == "parsed"


def test_ignore_pattern():
    r = parse("TESTBK", "TESTBANK: payment of INR 10.00 FAILED", BASE)
    assert (r.status, r.reason) == ("ignored", "failed payment")


def test_unknown_sender_and_unparsed():
    assert parse("NOBODY", "anything", BASE).status == "unknown_sender"
    assert parse("TESTBK", "TESTBANK: something new", BASE).status == "unparsed"


def test_card_target_and_kind():
    r = parse("TESTBK", "TESTBANK: INR 5,000.00 paid from a/c XX1111 to card XX9999", BASE)
    assert (r.parsed.kind, r.parsed.target_last4) == ("card_payment", "9999")


def _write(tmp_path, text):
    (tmp_path / "p.yaml").write_text(text)
    return tmp_path


@pytest.mark.parametrize(
    "body,fragment",
    [
        ("id: x\naccount_kind: card\nsenders: [XXXXXX]\npatterns:\n  - match: 'limit (?P<balance>\\d+) (?P<account>\\d+)'\n    type: balance\n", "may not capture a balance"),
        ("id: x\naccount_kind: bank\nsenders: [XXXXXX]\npatterns:\n  - match: 'a (?P<account>\\d+)'\n    direction: debit\n", "need groups"),
        ("id: x\naccount_kind: bank\nsenders: [XXXXXX]\npatterns:\n  - match: 'a (?P<account>\\d+) (?P<amount>\\d+)'\n", "direction"),
        ("id: x\naccount_kind: bank\nsenders: [XXXXXX]\npatterns:\n  - match: '('\n", "regex"),
        ("id: x\naccount_kind: bank\nsenders: [XXXXXX]\npatterns:\n  - match: 'a'\n    type: ignore\n", "reason"),
        ("id: x\naccount_kind: wallet\nsenders: [XXXXXX]\npatterns: []\n", "account_kind"),
    ],
)
def test_bad_profiles_are_rejected(tmp_path, settings, body, fragment):
    settings.INGEST_PROFILE_DIRS = [_write(tmp_path, body)]
    parser.clear_cache()
    with pytest.raises(ProfileError, match=fragment):
        parser.profiles()


def test_two_profiles_cannot_claim_one_sender(tmp_path, settings):
    one = "id: {id}\naccount_kind: bank\nsenders: [SAMEHD]\npatterns:\n  - match: 'a'\n    type: ignore\n    reason: r\n"
    (tmp_path / "a.yaml").write_text(one.format(id="a"))
    (tmp_path / "b.yaml").write_text(one.format(id="b"))
    settings.INGEST_PROFILE_DIRS = [tmp_path]
    parser.clear_cache()
    with pytest.raises(ProfileError, match="claimed by two"):
        parser.profiles()


def test_shipped_profiles_load(settings):
    from django.conf import settings as real

    settings.INGEST_PROFILE_DIRS = [real.BASE_DIR / "ingest" / "profiles"]
    parser.clear_cache()
    parser.profiles()  # every real profile must load


def test_date_without_year_takes_the_latest_past_date(settings, tmp_path):
    (tmp_path / "p.yaml").write_text(
        "id: noyear\naccount_kind: bank\nsenders: [NOYEAR]\ndate_formats: ['%d%b']\npatterns:\n"
        "  - id: c\n    direction: credit\n    match: 'X (?P<account>\\d{4}) (?P<amount>[\\d.]+) on (?P<date>\\d\\d[A-Z]{3})'\n"
    )
    settings.INGEST_PROFILE_DIRS = [tmp_path]
    parser.clear_cache()
    jan = dt.datetime(2027, 1, 5, 10, 0, tzinfo=parser.IST)
    assert parse("NOYEAR", "X 1111 5.00 on 30DEC", jan).parsed.occurred_at.date() == dt.date(2026, 12, 30)
    assert parse("NOYEAR", "X 1111 5.00 on 04JAN", jan).parsed.occurred_at.date() == dt.date(2027, 1, 4)
    assert parse("NOYEAR", "X 1111 5.00 on 29FEB", jan).parsed.occurred_at.date() == dt.date(2024, 2, 29)
