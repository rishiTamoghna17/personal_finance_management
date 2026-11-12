import pytest

from ingest.models import LedgerEntry, ReviewItem
from ingest.tasks import sweep

from .helpers import ingest

pytestmark = pytest.mark.django_db


@pytest.fixture
def send(firefly, django_capture_on_commit_callbacks):
    def _send(sender, text, minutes=0):
        return ingest(django_capture_on_commit_callbacks, sender, text, minutes)
    return _send


def test_withdrawal_payload(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 1,23,456.78 debited from a/c XX1111 to shop@upi on 12-11-26 ref 123456789012")
    assert sweep() == {"queued_posts": 1, "unpaired": 0}
    body = firefly.transactions[0]
    assert body["error_if_duplicate_hash"] is True
    tx = body["transactions"][0]
    entry = LedgerEntry.objects.get()
    assert tx == {
        "type": "withdrawal",
        "date": "2026-11-12T10:00:00+05:30",
        "amount": "123456.78",
        "currency_code": "INR",
        "description": "UPI shop@upi",
        "external_id": str(entry.external_id),
        "notes": f"bridge raw message ids: {entry.messages.get().raw_id}",
        "tags": ["bridge", "source-sms", "channel-upi"],
        "internal_reference": "123456789012",
        "source_id": "1",
        "destination_name": "shop@upi",
    }
    assert (entry.status, entry.firefly_group_id) == ("posted", "1")


def test_amounts_are_decimal_strings_never_floats(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 0.10 debited from a/c XX1111 to a@b on 12-11-26 ref 123456789012")
    sweep()
    assert firefly.transactions[0]["transactions"][0]["amount"] == "0.10"


def test_transfer_and_deposit_payloads(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 50.00 debited from a/c XX1111 to me@upi on 12-11-26 ref 111111111111")
    send("VM-TESTBK", "TESTBANK: INR 50.00 credited to a/c XX2222 from me@upi on 12-11-26 ref 111111111111", 1)
    send("VM-TESTCC", "TESTCARD: refund of INR 99.00 to card XX9999 from SHOP.", 2)
    sweep()
    by_type = {b["transactions"][0]["type"]: b["transactions"][0] for b in firefly.transactions}
    assert (by_type["transfer"]["source_id"], by_type["transfer"]["destination_id"]) == ("1", "2")
    assert (by_type["deposit"]["source_name"], by_type["deposit"]["destination_id"]) == ("SHOP", "3")


def test_sweep_does_not_post_twice(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 10.00 debited from a/c XX1111 to a@b on 12-11-26 ref 123456789012")
    sweep()
    sweep()
    assert len(firefly.transactions) == 1


def test_settle_window_holds_new_entries(send, firefly, settings):
    settings.INGEST_SETTLE_SECONDS = 600
    send("VM-TESTBK", "TESTBANK: INR 10.00 debited from a/c XX1111 to a@b on 12-11-26 ref 123456789012")
    assert sweep() == {"queued_posts": 0, "unpaired": 0}
    assert firefly.transactions == []


def test_cancelled_entries_are_never_posted(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 10.00 debited from a/c XX1111 to a@b on 12-11-26 ref 777777777777")
    send("VM-TESTBK", "TESTBANK: INR 10.00 reversed to a/c XX1111 ref 777777777777", 1)
    sweep()
    assert firefly.transactions == []


def test_unpaired_half_of_a_transfer_goes_to_review(send, firefly):
    send("VM-TESTCC", "TESTCARD: payment of INR 7,000.00 received on card XX9999")
    assert sweep() == {"queued_posts": 0, "unpaired": 1}
    assert firefly.transactions == []
    item = ReviewItem.objects.get()
    assert item.reason == "unpaired_transfer" and item.raw is not None


def test_firefly_rejection_goes_to_review(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 10.00 debited from a/c XX1111 to a@b on 12-11-26 ref 123456789012")
    firefly.fail_with = 422
    sweep()
    entry = LedgerEntry.objects.get()
    assert entry.status == "review"
    assert ReviewItem.objects.get().reason == "post_failed"


def test_payment_after_post_completing_a_transfer_is_flagged(send, firefly):
    send("VM-TESTBK", "TESTBANK: INR 50.00 debited from a/c XX1111 to me@upi on 12-11-26 ref 111111111111")
    sweep()
    send("VM-TESTBK", "TESTBANK: INR 50.00 credited to a/c XX2222 from me@upi on 12-11-26 ref 111111111111", 30)
    item = ReviewItem.objects.get()
    assert item.reason == "transfer_already_posted"
    assert LedgerEntry.objects.count() == 1
