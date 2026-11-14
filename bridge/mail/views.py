"""Tap-to-reconnect pages, opened in the phone's browser (no API token there, so no bearer auth). Access is by the
one-time link itself, and the bridge is only reachable over the private Tailscale address."""
import html
import logging

from django.http import HttpResponse, HttpResponseRedirect
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from . import reconnect

log = logging.getLogger(__name__)


def _page(title, text, status=200):
    body = (f"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>{html.escape(title)}"
            f"</title><body style='font:16px system-ui;padding:24px;max-width:520px;margin:auto'><h2>{html.escape(title)}</h2>"
            f"<p>{html.escape(text)}</p></body>")
    return HttpResponse(body, status=status, content_type="text/html; charset=utf-8")


class _Public(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]


class GoogleConnectView(_Public):
    """GET /api/v1/google/connect/<token>: from the reminder; sends the owner to Google's sign-in page."""

    def get(self, request, token):
        if not reconnect.enabled():
            return _page("Not available", "Reconnecting from the phone needs the private HTTPS address.", 404)
        try:
            return HttpResponseRedirect(reconnect.start(token))
        except reconnect.ReconnectError as exc:
            return _page("Link not valid", str(exc), 410)


class GoogleCallbackView(_Public):
    """GET /api/v1/google/callback: Google sends the owner back here after they allow access."""

    def get(self, request):
        if request.query_params.get("error"):
            return _page("Not connected", "Google sign-in was cancelled. Nothing changed; tap the link again to retry.", 400)
        try:
            label = reconnect.finish(request.query_params.get("state", ""), request.query_params.get("code", ""))
        except reconnect.ReconnectError as exc:
            return _page("Not connected", str(exc), 400)
        except Exception as exc:  # Google refused the code, network error, ...
            log.warning("google reconnect failed: %s", type(exc).__name__)
            return _page("Not connected", "Google did not accept the sign-in. Tap the link again to retry.", 400)
        log.info("google sign-in renewed: %s", label)
        return _page("Connected", f"{label} is connected again. You can close this page.")
