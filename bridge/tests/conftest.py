from pathlib import Path

import pytest
from django.core.cache import cache

from config import celery_app
from firefly.client import FireflyClient

from .fakes import FakeFirefly

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

TEST_PROFILES = Path(__file__).parent / "ingest" / "profiles"
HMAC_SECRET = "test-hmac-secret"


@pytest.fixture(autouse=True)
def _settings(settings):
    from ingest import parser

    settings.BRIDGE_API_TOKEN = "test-token"
    settings.FIREFLY_ACCESS_TOKEN = "firefly-test-token"
    settings.BRIDGE_SMS_HMAC_SECRET = HMAC_SECRET
    settings.INGEST_PROFILE_DIRS = [TEST_PROFILES]
    settings.INGEST_SETTLE_SECONDS = 0
    settings.INGEST_DEFAULT_ACCOUNTS = {}  # tests never depend on the owner's .env
    settings.INGEST_EMAIL_PROFILE_DIRS = [settings.BASE_DIR / "ingest" / "profiles" / "email"]
    settings.BRIDGE_ENCRYPTION_KEY = "jLbH5d5mF0eQ2m7O6l8kYJk9oQx3VtQGZ7m9c1fL3uU="
    settings.GMAIL_REQUEST_PAUSE_SECONDS = 0
    settings.LLM_FALLBACK_ENABLED = False  # LLM tests switch it on with a mocked model
    settings.LLM_PROVIDER = "ollama"
    settings.INGEST_OWN_VPAS = set()
    cache.clear()  # throttle counters and the account directory live in the cache
    parser.clear_cache()
    yield
    parser.clear_cache()


@pytest.fixture
def auth():
    return {"HTTP_AUTHORIZATION": "Bearer test-token"}


@pytest.fixture
def firefly(monkeypatch):
    """A fake Firefly with two bank accounts and one card, used by every module."""
    fake = FakeFirefly()
    fake.add(name="Bank A", type="asset", account_role="savingAsset", account_number="XX1111", active=True)
    fake.add(name="Bank B", type="asset", account_role="defaultAsset", account_number="XX2222", active=True)
    fake.add(name="Card C", type="asset", account_role="ccAsset", account_number="XX9999", active=True)
    monkeypatch.setattr(FireflyClient, "from_settings", classmethod(lambda cls: fake.client()))
    return fake
