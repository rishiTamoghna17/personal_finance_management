"""An in-memory stand-in for the Firefly API, plugged in as an httpx transport."""
import json

import httpx

from firefly.client import FireflyClient


class FakeFirefly:
    def __init__(self, page_size=50):
        self.accounts = []
        self.transactions = []
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
