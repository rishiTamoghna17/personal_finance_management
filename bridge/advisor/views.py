"""Advisor API for the Phase 2 app (and the temporary local test page). Read-only: nothing here can move money."""
from rest_framework.response import Response
from rest_framework.views import APIView

from firefly.client import FireflyError
from llm.providers import LLMError

from . import alerts, chat, digest


class ChatView(APIView):
    """POST /api/v1/chat {"message": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}"""

    def post(self, request):
        message = request.data.get("message") if isinstance(request.data, dict) else None
        if not isinstance(message, str) or not message.strip():
            return Response({"detail": "message is required"}, status=400)
        history = request.data.get("history") or []
        if not isinstance(history, list):
            return Response({"detail": "history must be a list"}, status=400)
        try:
            return Response(chat.answer(message.strip(), history))
        except FireflyError:
            return Response({"detail": "Firefly is unavailable."}, status=502)
        except LLMError as exc:
            return Response({"detail": f"The local model is unavailable ({exc})."}, status=503)


class DigestView(APIView):
    """GET /api/v1/digest?week=2026-W46 (default: the last complete Monday-Sunday week)."""

    def get(self, request):
        week = request.query_params.get("week")
        try:
            return Response(digest.build(week))
        except ValueError:
            return Response({"detail": "week must look like 2026-W46"}, status=400)
        except FireflyError:
            return Response({"detail": "Firefly is unavailable."}, status=502)


class AlertsView(APIView):
    """GET /api/v1/alerts"""

    def get(self, request):
        try:
            return Response({"alerts": alerts.build()})
        except FireflyError:
            return Response({"detail": "Firefly is unavailable."}, status=502)
