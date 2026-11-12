import pytest
from django.test import Client

URLS = ["/api/v1/health", "/api/v1/accounts"]


@pytest.mark.parametrize("url", URLS)
def test_no_token_is_rejected(url):
    assert Client().get(url).status_code == 401


@pytest.mark.parametrize("url", URLS)
@pytest.mark.parametrize("header", ["Bearer wrong", "Token test-token", "Bearer", "Bearer a b", "test-token"])
def test_bad_token_is_rejected(url, header):
    assert Client().get(url, HTTP_AUTHORIZATION=header).status_code == 401


def test_unset_token_never_matches(settings):
    settings.BRIDGE_API_TOKEN = ""
    assert Client().get("/api/v1/health", HTTP_AUTHORIZATION="Bearer ").status_code == 401
    assert Client().get("/api/v1/health", HTTP_AUTHORIZATION="Bearer x").status_code == 401


@pytest.mark.parametrize("url", URLS)
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_api_is_read_only(url, method, auth):
    assert getattr(Client(), method)(url, **auth).status_code == 405


def test_rate_limit_applies(auth, monkeypatch):
    from rest_framework.throttling import UserRateThrottle

    monkeypatch.setattr(UserRateThrottle, "THROTTLE_RATES", {"user": "2/min", "anon": "2/min"})
    monkeypatch.setattr("core.views.FireflyClient.from_settings", lambda: type("C", (), {"has_token": False})())
    client = Client()
    codes = [client.get("/api/v1/health", **auth).status_code for _ in range(3)]
    assert codes[-1] == 429
