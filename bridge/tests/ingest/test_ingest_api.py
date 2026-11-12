import json
import logging

import pytest

from ingest.models import DropTally, RawMessage, ReviewItem

from .helpers import ingest, post_sms

pytestmark = pytest.mark.django_db

DEBIT = "TESTBANK: INR 500.00 debited from a/c XX1111 to shop@upi on 12-11-26 ref 111111111111"
OTP = "482913 is your OTP for a payment of INR 500.00. Do not share it."


def test_requires_bearer_token(firefly):
    assert post_sms("VM-TESTBK", DEBIT, token=None).status_code == 401
    assert post_sms("VM-TESTBK", DEBIT, token="wrong").status_code == 401


def test_requires_valid_signature(firefly):
    assert post_sms("VM-TESTBK", DEBIT, signature="").status_code == 401
    assert post_sms("VM-TESTBK", DEBIT, signature="00" * 32).status_code == 401
    assert RawMessage.objects.count() == 0


def test_unset_hmac_secret_rejects_everything(firefly, settings):
    settings.BRIDGE_SMS_HMAC_SECRET = ""
    assert post_sms("VM-TESTBK", DEBIT, signature="").status_code == 401


@pytest.mark.parametrize(
    "extra",
    [{"sentStamp": "yesterday"}, {"sentStamp": 1768556698}, {"text": "x" * 2001}, {"from": None}, {"sentStamp": True}],
)
def test_bad_payload_is_rejected_without_echoing_it(firefly, extra):
    response = post_sms("VM-TESTBK", DEBIT, extra=extra)
    assert response.status_code == 400
    assert "debited" not in response.content.decode()
    assert RawMessage.objects.count() == 0


def test_sent_stamp_may_be_a_quoted_number(firefly, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = post_sms("VM-TESTBK", DEBIT, extra={"sentStamp": "1762921800000"})
    assert response.status_code == 202


def test_otp_is_dropped_before_anything_is_stored(firefly, caplog, django_capture_on_commit_callbacks):
    caplog.set_level(logging.DEBUG)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = post_sms("VM-TESTBK", OTP)
    assert response.status_code == 200 and response.json() == {"status": "dropped"}
    assert callbacks == []  # nothing queued
    assert RawMessage.objects.count() == 0 and ReviewItem.objects.count() == 0
    assert "482913" not in caplog.text
    tally = DropTally.objects.get()
    assert (tally.header, tally.count) == ("TESTBK", 1)
    post_sms("VM-TESTBK", OTP)
    tally.refresh_from_db()
    assert tally.count == 2
    # Nothing in the bridge database holds the code.
    for model in (RawMessage, ReviewItem, DropTally):
        assert "482913" not in json.dumps(list(model.objects.values()), default=str)


def test_accepted_message_is_processed(firefly, django_capture_on_commit_callbacks):
    body = ingest(django_capture_on_commit_callbacks, "VM-TESTBK-S", DEBIT)
    assert body["status"] == "accepted"
    raw = RawMessage.objects.get(pk=body["id"])
    assert (raw.status, raw.header, raw.pattern_ref) == ("parsed", "TESTBK", "testbank/upi-debit")


def test_redelivery_is_idempotent(firefly, django_capture_on_commit_callbacks):
    first = ingest(django_capture_on_commit_callbacks, "VM-TESTBK", DEBIT)
    second = ingest(django_capture_on_commit_callbacks, "VM-TESTBK", DEBIT)
    assert second == {"status": "duplicate", "id": first["id"]}
    assert RawMessage.objects.count() == 1


def test_unknown_sender_goes_to_review_not_dropped(firefly, django_capture_on_commit_callbacks):
    ingest(django_capture_on_commit_callbacks, "VM-OTHERX", "Hello there")
    item = ReviewItem.objects.get()
    assert item.reason == "unknown_sender" and item.raw.status == "review"


def test_unparsed_goes_to_review(firefly, django_capture_on_commit_callbacks):
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: a new kind of message")
    assert ReviewItem.objects.get().reason == "unparsed"


def test_ignored_message_is_kept_with_reason(firefly, django_capture_on_commit_callbacks):
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: payment of INR 10.00 FAILED")
    raw = RawMessage.objects.get()
    assert (raw.status, raw.status_reason) == ("ignored", "failed payment")


def test_unknown_account_goes_to_review(firefly, django_capture_on_commit_callbacks):
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", DEBIT.replace("XX1111", "XX5555"))
    item = ReviewItem.objects.get()
    assert item.reason == "unknown_account" and "5555" in item.detail


def test_firefly_down_leaves_message_received_for_retry(firefly, django_capture_on_commit_callbacks, monkeypatch):
    firefly.fail_with = 500
    from celery.exceptions import Retry

    with pytest.raises(Retry):
        ingest(django_capture_on_commit_callbacks, "VM-TESTBK", DEBIT)
    assert RawMessage.objects.get().status == "received"
