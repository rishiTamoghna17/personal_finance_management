from django.urls import path

from advisor.views import AlertsView, ChatView, DigestView
from core.views import HealthView
from firefly.views import AccountsView
from ingest.views import IngestEmailView, IngestSmsView, ReviewActionView, ReviewListView
from wealth.views import GoalsView, HoldingsView, NetWorthView, UpcomingView

# Versioned so the Phase 2 app can rely on /api/v1/ staying stable.
urlpatterns = [
    path("api/v1/health", HealthView.as_view(), name="health"),
    path("api/v1/accounts", AccountsView.as_view(), name="accounts"),
    path("api/v1/ingest/sms", IngestSmsView.as_view(), name="ingest-sms"),
    path("api/v1/ingest/email", IngestEmailView.as_view(), name="ingest-email"),
    path("api/v1/review", ReviewListView.as_view(), name="review-list"),
    path("api/v1/review/<int:pk>/<str:action>", ReviewActionView.as_view(), name="review-action"),
    path("api/v1/networth", NetWorthView.as_view(), name="networth"),
    path("api/v1/upcoming", UpcomingView.as_view(), name="upcoming"),
    path("api/v1/goals", GoalsView.as_view(), name="goals"),
    path("api/v1/holdings", HoldingsView.as_view(), name="holdings"),
    path("api/v1/chat", ChatView.as_view(), name="chat"),
    path("api/v1/digest", DigestView.as_view(), name="digest"),
    path("api/v1/alerts", AlertsView.as_view(), name="alerts"),
]
