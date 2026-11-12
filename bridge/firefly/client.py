"""Thin client for the Firefly III REST API (v1).

Firefly is the ledger. This client only reads, and creates accounts for the
one-off seed. Amounts cross this boundary as decimal strings, never floats.
"""
import httpx
from django.conf import settings


class FireflyError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class FireflyClient:
    def __init__(self, base_url, token, timeout=15, transport=None):
        self.has_token = bool(token)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/") + "/api/v1/",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls):
        return cls(settings.FIREFLY_BASE_URL, settings.FIREFLY_ACCESS_TOKEN, settings.FIREFLY_TIMEOUT_SECONDS)

    def _request(self, method, path, **kwargs):
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise FireflyError(f"Firefly unreachable: {type(exc).__name__}") from None
        if response.status_code >= 400:
            # Validation messages name fields, not secrets; keep them short for the operator.
            detail = ""
            try:
                detail = str(response.json().get("message", ""))[:200]
            except ValueError:
                pass
            raise FireflyError(f"Firefly {method} {path} -> {response.status_code} {detail}".strip(), response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def about(self):
        return self._request("GET", "about")["data"]

    def list_accounts(self, account_type):
        """All accounts of a Firefly type filter ("asset", "liabilities", ...), across pages."""
        accounts, page = [], 1
        while True:
            body = self._request("GET", "accounts", params={"type": account_type, "page": page, "limit": 50})
            accounts.extend(body.get("data", []))
            pagination = body.get("meta", {}).get("pagination", {})
            if page >= int(pagination.get("total_pages", 1)):
                return accounts
            page += 1

    def create_account(self, payload):
        return self._request("POST", "accounts", json=payload)["data"]

    def create_transaction(self, payload):
        """POST /transactions. Returns the created transaction group."""
        return self._request("POST", "transactions", json=payload)["data"]

    def enable_currency(self, code):
        # Firefly answers 415 to a POST with no Content-Type, so send an empty JSON body.
        return self._request("POST", f"currencies/{code}/enable", json={})

    def make_primary_currency(self, code):
        return self._request("POST", f"currencies/{code}/primary", json={})
