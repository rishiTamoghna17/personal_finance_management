import json

import pytest
from django.test import Client

from ingest.models import RawMessage
from tests.ingest.helpers import sign, stamp

pytestmark = pytest.mark.django_db


def post(payload, token="test-token"):
    body = json.dumps(payload).encode()
    return Client().post("/api/v1/ingest/email", data=body, content_type="application/json",
                         HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_SIGNATURE=sign(body))


def test_email_endpoint_drops_otp_and_accepts_alert(firefly, django_capture_on_commit_callbacks):
    otp = post({"from": "alerts@hdfcbank.bank.in", "subject": "OTP for your transaction", "text": "Your OTP is 482913", "sentStamp": stamp()})
    assert otp.json() == {"status": "dropped"} and RawMessage.objects.count() == 0
    with django_capture_on_commit_callbacks(execute=True):
        ok = post({"from": "HDFC <alerts@hdfcbank.bank.in>", "subject": "UPI txn",
                   "text": "Rs.45.00 is debited from your account ending 1111 towards VPA a@ybl (SHOP) on 12-11-26. "
                           "UPI transaction reference no.: 100000000501.", "sentStamp": stamp()})
    assert ok.status_code == 202
    assert RawMessage.objects.get().pattern_ref == "hdfc-email/upi-debit"


def test_email_endpoint_needs_token_and_signature(firefly):
    assert post({"from": "a@b.c", "subject": "", "text": "x", "sentStamp": stamp()}, token="bad").status_code == 401
