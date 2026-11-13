from django.urls import path

from core.views import HealthView
from firefly.views import AccountsView
from ingest.views import IngestEmailView, IngestSmsView, ReviewActionView, ReviewListView

# Versioned so the Phase 2 app can rely on /api/v1/ staying stable.
urlpatterns = [
    path("api/v1/health", HealthView.as_view(), name="health"),
    path("api/v1/accounts", AccountsView.as_view(), name="accounts"),
    path("api/v1/ingest/sms", IngestSmsView.as_view(), name="ingest-sms"),
    path("api/v1/ingest/email", IngestEmailView.as_view(), name="ingest-email"),
    path("api/v1/review", ReviewListView.as_view(), name="review-list"),
    path("api/v1/review/<int:pk>/<str:action>", ReviewActionView.as_view(), name="review-action"),
]
