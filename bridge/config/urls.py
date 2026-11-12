from django.urls import path

from core.views import HealthView
from firefly.views import AccountsView

# Versioned so the Phase 2 app can rely on /api/v1/ staying stable.
urlpatterns = [
    path("api/v1/health", HealthView.as_view(), name="health"),
    path("api/v1/accounts", AccountsView.as_view(), name="accounts"),
]
