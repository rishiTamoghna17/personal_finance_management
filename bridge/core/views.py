from django.core.cache import cache
from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView

from firefly.client import FireflyClient, FireflyError


def _check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _check_cache():
    cache.set("health:ping", "1", timeout=10)
    if cache.get("health:ping") != "1":
        raise RuntimeError("cache round trip failed")


class HealthView(APIView):
    """GET /api/v1/health - is the bridge able to reach what it depends on?"""

    def get(self, request):
        checks = {}
        for name, check in (("database", _check_database), ("cache", _check_cache)):
            try:
                check()
                checks[name] = "ok"
            except Exception:
                checks[name] = "error"

        client = FireflyClient.from_settings()
        if not client.has_token:
            checks["firefly"] = "token_missing"
        else:
            try:
                about = client.about()
                checks["firefly"] = "ok"
                checks["firefly_version"] = about.get("version")
            except FireflyError:
                checks["firefly"] = "error"

        healthy = all(checks[k] == "ok" for k in ("database", "cache", "firefly"))
        return Response({"status": "ok" if healthy else "degraded", "checks": checks}, status=200 if healthy else 503)
