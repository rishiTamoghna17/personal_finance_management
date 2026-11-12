import httpx
import pytest

from firefly.client import FireflyClient, FireflyError

from .fakes import FakeFirefly


def test_about():
    assert FakeFirefly().client().about()["version"] == "6.7.9"


def test_list_accounts_follows_pages():
    fake = FakeFirefly(page_size=2)
    for i in range(5):
        fake.add(name=f"A{i}", type="asset")
    fake.add(name="Loan", type="liabilities")
    client = fake.client()
    assert [a["attributes"]["name"] for a in client.list_accounts("asset")] == ["A0", "A1", "A2", "A3", "A4"]
    assert [a["attributes"]["name"] for a in client.list_accounts("liabilities")] == ["Loan"]


def test_http_error_becomes_firefly_error():
    fake = FakeFirefly()
    fake.fail_with = 422
    with pytest.raises(FireflyError) as info:
        fake.client().about()
    assert info.value.status_code == 422


def test_network_error_does_not_leak_details():
    def boom(request):
        raise httpx.ConnectError("connect to http://secret-host failed")

    client = FireflyClient("http://firefly.test", "tok", transport=httpx.MockTransport(boom))
    with pytest.raises(FireflyError) as info:
        client.about()
    assert "secret-host" not in str(info.value)


def test_has_token():
    assert FireflyClient("http://x", "").has_token is False
    assert FireflyClient("http://x", "t").has_token is True
