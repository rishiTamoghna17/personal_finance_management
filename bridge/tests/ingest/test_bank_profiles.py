"""Every real bank profile against the owner's masked samples (SPEC "Tests required")."""
import datetime as dt
from pathlib import Path

import pytest
import yaml

from ingest import parser
from ingest.otp import contains_secret, contains_secret_email

from .helpers import BASE

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*/*.yaml"))
EMAIL_FIXTURES = sorted((Path(__file__).parent / "fixtures" / "email").glob("*/*.yaml"))


@pytest.fixture(autouse=True)
def real_profiles(settings):
    settings.INGEST_PROFILE_DIRS = [settings.BASE_DIR / "ingest" / "profiles"]
    settings.INGEST_EMAIL_PROFILE_DIRS = [settings.BASE_DIR / "ingest" / "profiles" / "email"]
    parser.clear_cache()


def test_every_real_profile_has_a_fixture():
    profile_ids = {p.id for p in parser.profiles().values()} | {p.id for p in parser.profiles("email").values()}
    assert profile_ids <= {f.parent.name for f in FIXTURES + EMAIL_FIXTURES}


@pytest.mark.parametrize("path", FIXTURES + EMAIL_FIXTURES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_fixture(path):
    case = yaml.safe_load(path.read_text())
    expect = case["expect"]
    source = case.get("source", "sms")
    if source == "email":
        subject, _, body = case["text"].partition("\n")
        secret = contains_secret_email(subject, body)
        header = parser.header_of_email(case["sender"])
    else:
        secret = contains_secret(case["text"])
        header = parser.header_of(case["sender"])
    if expect["status"] == "dropped":
        assert secret, "a message with a code must be dropped"
        return
    assert not secret, "a real alert must not be dropped as a secret"
    assert parser.profiles(source)[header].id == path.parent.name
    result = parser.parse(header, case["text"], BASE, source)
    assert result.status == expect["status"], result.reason
    if result.status == "unparsed":
        return
    if result.status in ("ignored", "review"):
        assert result.reason == expect["reason"]
        return
    p = result.parsed
    for field in ("amount_paise", "direction", "channel", "account_last4", "counterparty", "reference", "vpa",
                  "kind", "target_last4", "balance_paise"):
        if field in expect:
            assert getattr(p, field) == expect[field], field
    local = p.occurred_at.astimezone(parser.IST)
    if "date" in expect:
        assert local.date() == dt.date.fromisoformat(expect["date"])
    if "time" in expect:
        assert local.time() == dt.time.fromisoformat(expect["time"])


def test_every_real_pattern_has_a_fixture():
    covered = set()
    for path in FIXTURES + EMAIL_FIXTURES:
        case = yaml.safe_load(path.read_text())
        if case["expect"]["status"] in ("dropped", "unparsed"):
            continue
        source = case.get("source", "sms")
        header = parser.header_of_email(case["sender"]) if source == "email" else parser.header_of(case["sender"])
        covered.add(parser.parse(header, case["text"], BASE, source).pattern_ref)
    patterns = {pat.ref for src in ("sms", "email") for prof in set(parser.profiles(src).values()) for pat in prof.patterns}
    assert patterns - covered == set()
