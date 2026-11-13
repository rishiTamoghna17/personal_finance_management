import io

import pytest
import yaml
from django.core.management import call_command
from django.core.management.base import CommandError

from firefly.management.commands import seed_firefly
from firefly.seed import SeedError, build_plan

from .fakes import FakeFirefly

GOOD = """
opening_balance_date: "2026-11-01"
accounts:
  - {name: "Bank One Savings", kind: bank, role: savings, last4: "1234", opening_balance: "1,50,000.50"}
  - {name: "Bank Two Salary", kind: bank, role: salary, opening_balance: "0.00"}
  - {name: "Card One", kind: credit_card, last4: "9876", outstanding: "12345.67", next_payment_due: 2026-12-05}
  - {name: "Bike Loan", kind: loan, status: planned}
  - {name: "Old Loan", kind: loan, status: active, outstanding: "200000.00", interest_rate_percent: "9.50"}
"""


def test_build_plan():
    payloads, planned = build_plan(yaml.safe_load(GOOD))
    assert planned == ["Bike Loan"]
    by_name = {p["name"]: p for p in payloads}
    assert set(by_name) == {"Bank One Savings", "Bank Two Salary", "Card One", "Old Loan"}

    savings = by_name["Bank One Savings"]
    assert savings["type"] == "asset" and savings["account_role"] == "savingAsset"
    assert savings["account_number"] == "XX1234" and savings["currency_code"] == "INR"
    assert savings["opening_balance"] == "150000.50" and savings["opening_balance_date"] == "2026-11-01"

    assert by_name["Bank Two Salary"]["opening_balance"] == "0.00"  # sent so a re-run can correct it

    card = by_name["Card One"]
    assert card["account_role"] == "ccAsset" and card["opening_balance"] == "-12345.67"
    assert card["monthly_payment_date"] == "2026-12-05"

    loan = by_name["Old Loan"]
    assert loan["type"] == "liability" and loan["liability_type"] == "loan"
    assert loan["liability_direction"] == "debit" and loan["opening_balance"] == "200000.00"

    for payload in payloads:  # decimal strings only, never floats
        assert not any(isinstance(v, float) for v in payload.values())


@pytest.mark.parametrize(
    "entry,fragment",
    [
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": 1500.5}, "quoted string"),
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": 1500}, "quoted string"),
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": "-5.00"}, "negative"),
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": "1.005"}, "paisa"),
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": "1.00", "last4": "50100123456789"}, "four digits"),
        ({"name": "A", "kind": "bank", "role": "savings", "opening_balance": "1.00", "last4": 1234}, "four digits"),
        ({"name": "A", "kind": "bank", "role": "gold", "opening_balance": "1.00"}, "role"),
        ({"name": "A", "kind": "wallet"}, "kind"),
        ({"name": "A", "kind": "credit_card", "outstanding": "1.00"}, "next_payment_due"),
        ({"name": "A", "kind": "loan", "outstanding": "1.00"}, "status"),
        ({"name": "A", "kind": "loan", "status": "active", "outstanding": "1.00", "interest_rate_percent": 9.5}, "interest_rate_percent"),
        ({"kind": "bank"}, "name is required"),
    ],
)
def test_build_plan_rejects(entry, fragment):
    with pytest.raises(SeedError, match=fragment):
        build_plan({"opening_balance_date": "2026-11-01", "accounts": [entry]})


def test_build_plan_rejects_duplicates_and_bad_files():
    entry = {"name": "A", "kind": "bank", "role": "savings", "opening_balance": "1.00"}
    with pytest.raises(SeedError, match="duplicate"):
        build_plan({"opening_balance_date": "2026-11-01", "accounts": [entry, dict(entry, name="a ")]})
    with pytest.raises(SeedError, match="opening_balance_date"):
        build_plan({"accounts": [entry]})
    with pytest.raises(SeedError, match="accounts"):
        build_plan(None)


def _run(tmp_path, monkeypatch, fake, *args):
    path = tmp_path / "accounts.yaml"
    path.write_text(GOOD)
    monkeypatch.setattr(seed_firefly.Command, "get_client", lambda self: fake.client())
    out = io.StringIO()
    call_command("seed_firefly", str(path), *args, stdout=out)
    return out.getvalue()


def test_seed_creates_then_is_idempotent(tmp_path, monkeypatch):
    fake = FakeFirefly()
    first = _run(tmp_path, monkeypatch, fake)
    assert first.count("created  ") == 4 and "planned  Bike Loan" in first
    assert ("POST", "currencies/INR/enable") in fake.calls and ("POST", "currencies/INR/primary") in fake.calls
    assert len(fake.accounts) == 4
    assert "Bike Loan" not in {a["attributes"]["name"] for a in fake.accounts}

    second = _run(tmp_path, monkeypatch, fake)
    assert second.count("exists") == 4 and "created  " not in second and "updated" not in second
    assert len(fake.accounts) == 4


def test_seed_corrects_digits_and_balances_of_existing_accounts(tmp_path, monkeypatch):
    fake = FakeFirefly()
    _run(tmp_path, monkeypatch, fake)
    path = tmp_path / "accounts.yaml"
    path.write_text(GOOD.replace('last4: "1234"', 'last4: "7378"').replace('outstanding: "12345.67"', 'outstanding: "0.00"'))
    out = io.StringIO()
    call_command("seed_firefly", str(path), stdout=out)
    out = out.getvalue()
    assert out.count("updated") == 2 and out.count("exists") == 2
    by_name = {a["attributes"]["name"]: a["attributes"] for a in fake.accounts}
    assert by_name["Bank One Savings"]["account_number"] == "XX7378"
    assert by_name["Card One"]["opening_balance"] == "0.00"
    assert len(fake.accounts) == 4


def test_seed_output_has_no_amounts_or_account_numbers(tmp_path, monkeypatch):
    out = _run(tmp_path, monkeypatch, FakeFirefly())
    for secret in ("150000", "12345.67", "1234", "9876", "200000"):
        assert secret not in out


def test_cash_account():
    payloads, _ = build_plan({"opening_balance_date": "2026-11-01",
                              "accounts": [{"name": "Cash", "kind": "cash", "opening_balance": "2,500.00"}]})
    assert payloads[0]["account_role"] == "cashWalletAsset" and payloads[0]["opening_balance"] == "2500.00"
    assert "account_number" not in payloads[0]


def test_seed_dry_run_touches_nothing(tmp_path, monkeypatch):
    fake = FakeFirefly()
    out = _run(tmp_path, monkeypatch, fake, "--dry-run")
    assert out.count("valid") == 4 and fake.calls == []


def test_seed_needs_a_token(tmp_path, monkeypatch, settings):
    settings.FIREFLY_ACCESS_TOKEN = ""
    path = tmp_path / "accounts.yaml"
    path.write_text(GOOD)
    with pytest.raises(CommandError, match="FIREFLY_ACCESS_TOKEN"):
        call_command("seed_firefly", str(path))


def test_example_file_is_valid():
    import pathlib

    example = pathlib.Path(__file__).resolve().parents[2] / "accounts.example.yaml"
    if example.exists():  # not present inside the Docker image
        build_plan(yaml.safe_load(example.read_text()))


def test_renamed_account_is_updated_not_duplicated(tmp_path, monkeypatch):
    fake = FakeFirefly()
    _run(tmp_path, monkeypatch, fake)
    path = tmp_path / "accounts.yaml"
    path.write_text(GOOD.replace('"Card One"', '"Card One Renamed"'))
    out = io.StringIO()
    call_command("seed_firefly", str(path), stdout=out)
    assert "updated  Card One Renamed" in out.getvalue()
    names = {a["attributes"]["name"] for a in fake.accounts}
    assert "Card One Renamed" in names and "Card One" not in names and len(fake.accounts) == 4
