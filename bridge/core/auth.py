"""Single-user bearer-token authentication for the bridge API."""
import hmac

from django.conf import settings
from rest_framework import authentication, exceptions


class BridgeOwner:
    """The one and only API user. Not a database row."""

    is_authenticated = True
    is_active = True
    pk = "owner"

    def __str__(self):
        return "owner"


class BridgeTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("latin-1")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")
        expected = settings.BRIDGE_API_TOKEN
        if not expected:
            # An unset token must never match an empty header value.
            raise exceptions.AuthenticationFailed("API token is not configured.")
        if not hmac.compare_digest(parts[1].encode(), expected.encode()):
            raise exceptions.AuthenticationFailed("Invalid token.")
        return (BridgeOwner(), None)

    def authenticate_header(self, request):
        return self.keyword
