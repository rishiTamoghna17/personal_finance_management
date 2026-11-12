from django.test import Client

from .fakes import FakeFirefly


def _use(monkeypatch, fake):
    monkeypatch.setattr("core.views.FireflyClient.from_settings", fake.client)
    monkeypatch.setattr("firefly.views.FireflyClient.from_settings", fake.client)


def test_health_ok(monkeypatch, auth, db):
    _use(monkeypatch, FakeFirefly())
    response = Client().get("/api/v1/health", **auth)
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "cache": "ok", "firefly": "ok", "firefly_version": "6.7.9"},
    }


def test_health_degraded_when_firefly_fails(monkeypatch, auth, db):
    fake = FakeFirefly()
    fake.fail_with = 500
    _use(monkeypatch, fake)
    response = Client().get("/api/v1/health", **auth)
    assert response.status_code == 503
    assert response.json()["checks"]["firefly"] == "error"


def test_health_reports_missing_firefly_token(settings, auth, db):
    settings.FIREFLY_ACCESS_TOKEN = ""
    response = Client().get("/api/v1/health", **auth)
    assert response.status_code == 503
    assert response.json()["checks"]["firefly"] == "token_missing"


def test_accounts(monkeypatch, auth, db):
    fake = FakeFirefly()
    fake.add(name="Bank One Savings", type="asset", account_role="savingAsset", account_number="XX1234",
             current_balance="150000.500000000000", active=True, include_net_worth=True)
    fake.add(name="Card One", type="asset", account_role="ccAsset", account_number="XX9876",
             current_balance="-12345.670000000000", active=True, include_net_worth=True)
    fake.add(name="Bike Loan", type="liabilities", liability_type="loan", account_number=None,
             current_balance="-200000.000000000000", active=True, include_net_worth=True)
    _use(monkeypatch, fake)

    response = Client().get("/api/v1/accounts", **auth)
    assert response.status_code == 200
    accounts = {a["name"]: a for a in response.json()["accounts"]}
    assert accounts["Bank One Savings"] | {"id": "x"} == {
        "id": "x", "name": "Bank One Savings", "kind": "asset", "role": "savingAsset", "liability_type": None,
        "last4": "1234", "currency": "INR", "balance_paise": 15000050, "balance_status": "calculated",
        "active": True, "include_net_worth": True, "bank_balance": None,
    }
    assert accounts["Card One"]["kind"] == "credit_card"
    assert accounts["Card One"]["balance_paise"] == -1234567
    assert accounts["Bike Loan"]["kind"] == "liability"
    assert accounts["Bike Loan"]["last4"] is None
    assert all(isinstance(a["balance_paise"], int) for a in accounts.values())


def test_accounts_never_returns_a_full_account_number(monkeypatch, auth, db):
    fake = FakeFirefly()
    fake.add(name="Typed In Full", type="asset", account_role="defaultAsset", account_number="50100123456789")
    _use(monkeypatch, fake)
    body = Client().get("/api/v1/accounts", **auth).content.decode()
    assert "50100123456789" not in body
    assert '"last4":"6789"' in body


def test_accounts_when_firefly_is_down(monkeypatch, auth, db):
    fake = FakeFirefly()
    fake.fail_with = 500
    _use(monkeypatch, fake)
    assert Client().get("/api/v1/accounts", **auth).status_code == 502


def test_accounts_without_firefly_token(settings, auth):
    settings.FIREFLY_ACCESS_TOKEN = ""
    assert Client().get("/api/v1/accounts", **auth).status_code == 503


def test_bank_reported_balance_status(monkeypatch, auth, db):
    import datetime as dt

    from django.utils import timezone

    from ingest.models import BalanceObservation, RawMessage

    fake = FakeFirefly()
    fake.add(name="Fresh", type="asset", account_role="savingAsset", account_number="XX1111", current_balance="10.00")
    fake.add(name="Old", type="asset", account_role="savingAsset", account_number="XX2222", current_balance="10.00")
    _use(monkeypatch, fake)
    now = timezone.now()
    for i, (acct, age) in enumerate((("1", dt.timedelta(hours=1)), ("2", dt.timedelta(days=10)))):
        raw = RawMessage.objects.create(source="sms", sender="s", header="h", body="b", sent_at=now, content_hash=str(i))
        BalanceObservation.objects.create(firefly_account_id=acct, balance_paise=123400, observed_at=now - age, raw=raw)
    accounts = {a["name"]: a for a in Client().get("/api/v1/accounts", **auth).json()["accounts"]}
    assert accounts["Fresh"]["balance_status"] == "confirmed"
    assert accounts["Fresh"]["bank_balance"]["balance_paise"] == 123400
    assert accounts["Fresh"]["balance_paise"] == 1000  # ledger figure is kept alongside
    assert accounts["Old"]["balance_status"] == "stale"
