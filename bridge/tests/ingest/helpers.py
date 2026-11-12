import datetime as dt
import hashlib
import hmac
import json

from django.test import Client

from ..conftest import HMAC_SECRET

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
BASE = dt.datetime(2026, 11, 12, 10, 0, tzinfo=IST)


def stamp(minutes=0, base=BASE):
    return int((base + dt.timedelta(minutes=minutes)).timestamp() * 1000)


def sign(body, secret=HMAC_SECRET):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def post_sms(sender, text, minutes=0, token="test-token", signature=None, extra=None, base=BASE):
    payload = {"from": sender, "text": text, "sentStamp": stamp(minutes, base), "receivedStamp": stamp(minutes, base)}
    payload.update(extra or {})
    body = json.dumps(payload).encode()
    headers = {"HTTP_X_SIGNATURE": sign(body) if signature is None else signature}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return Client().post("/api/v1/ingest/sms", data=body, content_type="application/json", **headers)


def ingest(capture, sender, text, minutes=0, base=BASE):
    """Post an SMS and run the processing that would follow the commit."""
    with capture(execute=True):
        response = post_sms(sender, text, minutes, base=base)
    assert response.status_code in (200, 202), response.content
    return response.json()
