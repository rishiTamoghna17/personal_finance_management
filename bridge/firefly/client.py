"""Thin client for the Firefly III REST API (v1).

Firefly is the ledger. This client reads, and writes only ledger records (accounts, transactions, categories,
goals, bills); nothing here can move money. Amounts cross this boundary as decimal strings, never floats.
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

    def list_accounts(self, account_type, on_date=None):
        """All accounts of a Firefly type filter ("asset", "liabilities", ...), across pages.
        With on_date, current_balance is the balance at the end of that day."""
        accounts, page = [], 1
        while True:
            params = {"type": account_type, "page": page, "limit": 50}
            if on_date:
                params["date"] = on_date.isoformat()
            body = self._request("GET", "accounts", params=params)
            accounts.extend(body.get("data", []))
            pagination = body.get("meta", {}).get("pagination", {})
            if page >= int(pagination.get("total_pages", 1)):
                return accounts
            page += 1

    def create_account(self, payload):
        return self._request("POST", "accounts", json=payload)["data"]

    def update_account(self, account_id, payload):
        return self._request("PUT", f"accounts/{account_id}", json=payload)["data"]

    def create_transaction(self, payload):
        """POST /transactions. Returns the created transaction group."""
        return self._request("POST", "transactions", json=payload)["data"]

    def list_all(self, path):
        items, page = [], 1
        while True:
            body = self._request("GET", path, params={"page": page, "limit": 50})
            items.extend(body.get("data", []))
            if page >= int(body.get("meta", {}).get("pagination", {}).get("total_pages", 1)):
                return items
            page += 1

    def create_category(self, name, notes):
        return self._request("POST", "categories", json={"name": name, "notes": notes})["data"]

    def update_category(self, category_id, name, notes):
        return self._request("PUT", f"categories/{category_id}", json={"name": name, "notes": notes})["data"]

    def create_webhook(self, payload):
        return self._request("POST", "webhooks", json=payload)["data"]

    def enable_currency(self, code):
        # Firefly answers 415 to a POST with no Content-Type, so send an empty JSON body.
        return self._request("POST", f"currencies/{code}/enable", json={})

    def make_primary_currency(self, code):
        return self._request("POST", f"currencies/{code}/primary", json={})

    # --- M5: balances on a date, goals (piggy banks), bills, spending totals ---
    def get_account(self, account_id, on_date=None):
        params = {"date": on_date.isoformat()} if on_date else None
        return self._request("GET", f"accounts/{account_id}", params=params)["data"]

    def create_piggy_bank(self, payload):
        return self._request("POST", "piggy-banks", json=payload)["data"]

    def update_piggy_bank(self, piggy_id, payload):
        return self._request("PUT", f"piggy-banks/{piggy_id}", json=payload)["data"]

    def create_bill(self, payload):
        return self._request("POST", "bills", json=payload)["data"]

    def update_bill(self, bill_id, payload):
        return self._request("PUT", f"bills/{bill_id}", json=payload)["data"]

    def expense_by_payee(self, start, end):
        """[(expense account name, amount spent as a positive decimal string)] between two dates, INR only."""
        body = self._request("GET", "insight/expense/expense", params={"start": start.isoformat(), "end": end.isoformat()})
        rows = body if isinstance(body, list) else body.get("data", [])
        return [(r.get("name", ""), str(r.get("difference", "0")).lstrip("-")) for r in rows if r.get("currency_code") == "INR"]
