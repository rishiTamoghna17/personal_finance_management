import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.BRIDGE_API_TOKEN = "test-token"
    settings.FIREFLY_ACCESS_TOKEN = "firefly-test-token"
    cache.clear()  # throttle counters live in the cache


@pytest.fixture
def auth():
    return {"HTTP_AUTHORIZATION": "Bearer test-token"}
