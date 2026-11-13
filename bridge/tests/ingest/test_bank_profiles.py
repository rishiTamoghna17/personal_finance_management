"""Every real bank profile against the owner's masked samples (SPEC "Tests required")."""
import datetime as dt
from pathlib import Path

import pytest
import yaml

from ingest import parser
from ingest.otp import contains_secret

from .helpers import BASE

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*/*.yaml"))


@pytest.fixture(autouse=True)
def real_profiles(settings):
    settings.INGEST_PROFILE_DIRS = [settings.BASE_DIR / "ingest" / "profiles"]
    parser.clear_cache()


def test_every_real_profile_has_a_fixture():
    profile_ids = {p.id for p in parser.profiles().values()}
    assert profile_ids <= {f.parent.name for f in FIXTURES}


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_fixture(path):
    case = yaml.safe_load(path.read_text())
    expect = case["expect"]
    if expect["status"] == "dropped":
        assert contains_secret(case["text"]), "a message with a code must be dropped"
        return
    assert not contains_secret(case["text"]), "a real alert must not be dropped as a secret"
    header = parser.header_of(case["sender"])
    assert parser.profiles()[header].id == path.parent.name
    result = parser.parse(header, case["text"], BASE)
    assert result.status == expect["status"], result.reason
    if result.status == "unparsed":
        return
    if result.status == "ignored":
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
    for path in FIXTURES:
        case = yaml.safe_load(path.read_text())
        if case["expect"]["status"] in ("dropped", "unparsed"):
            continue
        header = parser.header_of(case["sender"])
        covered.add(parser.parse(header, case["text"], BASE).pattern_ref)
    patterns = {pat.ref for prof in set(parser.profiles().values()) for pat in prof.patterns}
    assert patterns - covered == set()
