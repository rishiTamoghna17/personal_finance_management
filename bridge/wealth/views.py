"""Read-only M5 endpoints for the advisor (M6) and the future app. Money is integer paise."""
import datetime as dt

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from firefly.client import FireflyError

from . import dues, goals, networth
from .models import CasStatement, NetWorthSnapshot


def _firefly_down():
    return Response({"detail": "Firefly is unavailable."}, status=502)


class NetWorthView(APIView):
    """GET /api/v1/networth - now (live from Firefly) and the stored month-end history."""

    def get(self, request):
        try:
            now = networth.compute()
        except FireflyError:
            return _firefly_down()
        history = [{"date": s.taken_on.isoformat(), "assets_paise": s.assets_paise,
                    "liabilities_paise": s.liabilities_paise, "net_worth_paise": s.net_worth_paise}
                   for s in NetWorthSnapshot.objects.order_by("-taken_on")[:24]]
        return Response({"as_of": timezone.now().isoformat(), **now, "history": history})


class UpcomingView(APIView):
    """GET /api/v1/upcoming?days=30 - EMIs and card dues coming up, and dues that passed unpaid."""

    def get(self, request):
        try:
            days = max(1, min(120, int(request.query_params.get("days", 30))))
        except ValueError:
            days = 30
        return Response({"days": days, "items": dues.upcoming(days)})


class GoalsView(APIView):
    """GET /api/v1/goals - progress of each goal and what is needed per month."""

    def get(self, request):
        try:
            return Response({"goals": goals.progress(timezone.localdate())})
        except FireflyError:
            return _firefly_down()


class HoldingsView(APIView):
    """GET /api/v1/holdings - investments as stated by the latest CAS (no prices fetched or guessed)."""

    def get(self, request):
        cas = CasStatement.objects.order_by("-statement_date").first()
        if cas is None:
            return Response({"statement_date": None, "total_paise": 0, "holdings": []})
        rows = [{"kind": h.kind, "isin": h.isin, "name": h.name, "units": h.units, "price": h.price,
                 "value_paise": h.value_paise} for h in cas.holdings.order_by("-value_paise")]
        age = (timezone.localdate() - cas.statement_date).days
        return Response({"statement_date": cas.statement_date.isoformat(), "age_days": age,
                         "total_paise": cas.total_paise, "holdings": rows})
