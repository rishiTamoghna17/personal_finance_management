"""An in-memory stand-in for the Firefly API, plugged in as an httpx transport."""
import json

import httpx

from firefly.client import FireflyClient


class FakeFirefly:
    def __init__(self, page_size=50):
        self.accounts = []
        self.transactions = []
        self.categories = []
        self.webhooks = []
        self.piggy_banks = []
        self.bills = []
        self.expenses = []  # [(payee name, "123.45")] returned by insight/expense/expense
        self.calls = []
        self.fail_with = None
        self.page_size = page_size

    def add(self, **attributes):
        attributes.setdefault("current_balance", "0.000000000000")
        attributes.setdefault("currency_code", "INR")
        self.accounts.append({"id": str(len(self.accounts) + 1), "type": "accounts", "attributes": attributes})

    def handler(self, request):
        path = request.url.path.removeprefix("/api/v1/")
        self.calls.append((request.method, path))
        assert request.headers["Authorization"].startswith("Bearer ")
        if request.method == "POST" and not request.headers.get("Content-Type"):
            return httpx.Response(415, json={"message": "Content-Type header cannot be empty."})  # as real Firefly does
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": "boom"})
        if request.method == "GET" and path == "about":
            return httpx.Response(200, json={"data": {"version": "6.7.9", "api_version": "6.7.9"}})
        if request.method == "POST" and path.startswith("currencies/"):
            return httpx.Response(200, json={"data": {}})
        if request.method == "GET" and path == "accounts":
            wanted = request.url.params["type"]
            page = int(request.url.params.get("page", 1))
            rows = [a for a in self.accounts if (a["attributes"]["type"] == "liabilities") == (wanted == "liabilities")]
            total_pages = max(1, -(-len(rows) // self.page_size))
            chunk = rows[(page - 1) * self.page_size : page * self.page_size]
            return httpx.Response(200, json={"data": chunk, "meta": {"pagination": {"total_pages": total_pages}}})
        if request.method == "GET" and path == "insight/expense/expense":
            rows = [{"name": n, "difference": "-" + a, "currency_code": "INR"} for n, a in self.expenses]
            return httpx.Response(200, json=rows)
        if request.method == "GET" and path.startswith("accounts/"):
            account = next(a for a in self.accounts if a["id"] == path.split("/")[1])
            return httpx.Response(200, json={"data": account})
        if path.split("/")[0] in ("piggy-banks", "bills") and request.method == "PUT":
            store = self.piggy_banks if path.startswith("piggy") else self.bills
            item = next(i for i in store if i["id"] == path.split("/")[1])
            item["attributes"].update(json.loads(request.content))
            return httpx.Response(200, json={"data": item})
        if path in ("categories", "webhooks", "piggy-banks", "bills"):
            store = {"categories": self.categories, "webhooks": self.webhooks, "piggy-banks": self.piggy_banks,
                     "bills": self.bills}[path]
            if request.method == "GET":
                return httpx.Response(200, json={"data": store, "meta": {"pagination": {"total_pages": 1}}})
            body = json.loads(request.content)
            store.append({"id": str(len(store) + 1), "attributes": body})
            return httpx.Response(200, json={"data": store[-1]})
        if request.method == "PUT" and path.startswith("categories/"):
            item = next(c for c in self.categories if c["id"] == path.split("/")[1])
            item["attributes"].update(json.loads(request.content))
            return httpx.Response(200, json={"data": item})
        if request.method == "POST" and path == "transactions":
            body = json.loads(request.content)
            self.transactions.append(body)
            return httpx.Response(200, json={"data": {"type": "transactions", "id": str(len(self.transactions))}})
        if request.method == "PUT" and path.startswith("accounts/"):
            body = json.loads(request.content)
            account = next(a for a in self.accounts if a["id"] == path.split("/")[1])
            body.pop("type", None)
            account["attributes"].update(body)
            return httpx.Response(200, json={"data": account})
        if request.method == "POST" and path == "accounts":
            body = json.loads(request.content)
            body["type"] = "liabilities" if body["type"] == "liability" else body["type"]
            self.add(**body)
            return httpx.Response(200, json={"data": self.accounts[-1]})
        return httpx.Response(404, json={"message": "not found"})

    def client(self):
        return FireflyClient("http://firefly.test", "firefly-test-token", transport=httpx.MockTransport(self.handler))
