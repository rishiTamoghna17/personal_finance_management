import pytest
from django.test import Client

from ingest.models import LedgerEntry, RawMessage, ReviewItem
from ingest.tasks import sweep

from .helpers import ingest

pytestmark = pytest.mark.django_db


@pytest.fixture
def send(firefly, django_capture_on_commit_callbacks):
    def _send(sender, text, minutes=0):
        return ingest(django_capture_on_commit_callbacks, sender, text, minutes)
    return _send


def _post(url, auth, data=None):
    return Client().post(url, data=data or {}, content_type="application/json", **auth)


def test_review_needs_token(firefly):
    assert Client().get("/api/v1/review").status_code == 401


def test_list_and_ignore(send, auth):
    send("VM-OTHERX", "Some message")
    items = Client().get("/api/v1/review", **auth).json()["items"]
    assert len(items) == 1 and items[0]["message"]["text"] == "Some message"
    response = _post(f"/api/v1/review/{items[0]['id']}/ignore", auth)
    assert response.status_code == 200 and response.json()["status"] == "ignored"
    assert RawMessage.objects.get().status == "ignored"
    assert Client().get("/api/v1/review", **auth).json()["items"] == []
    assert _post(f"/api/v1/review/{items[0]['id']}/ignore", auth).status_code == 409


def test_reparse_after_a_profile_is_added(send, auth, settings, tmp_path):
    send("VM-NEWBNK", "NEWBANK: INR 75.00 debited from a/c XX1111")
    item = ReviewItem.objects.get()
    assert item.reason == "unknown_sender"
    (tmp_path / "newbank.yaml").write_text(
        "id: newbank\naccount_kind: bank\nsenders: [NEWBNK]\npatterns:\n"
        "  - id: debit\n    direction: debit\n    match: 'NEWBANK: INR (?P<amount>[\\d.]+) debited from a/c XX(?P<account>\\d{4})'\n"
    )
    settings.INGEST_PROFILE_DIRS = settings.INGEST_PROFILE_DIRS + [tmp_path]
    response = _post(f"/api/v1/review/{item.pk}/reparse", auth)
    assert response.status_code == 200 and response.json()["message_status"] == "parsed"
    assert LedgerEntry.objects.get().amount_paise == 7500


def test_resolve_ambiguous_by_merging(send, auth):
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA on 12-11-26")
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at CAFE on 12-11-26", 1)
    send("VM-TESTCC", "TESTCARD ALERT: card XX9999 used for INR 20.00", 2)
    item = ReviewItem.objects.get()
    assert _post(f"/api/v1/review/{item.pk}/resolve", auth, {"entry_id": 99999}).status_code == 400
    response = _post(f"/api/v1/review/{item.pk}/resolve", auth, {"entry_id": item.candidates[0]})
    assert response.status_code == 200
    assert LedgerEntry.objects.get(pk=item.candidates[0]).messages.count() == 2
    assert LedgerEntry.objects.count() == 2


def test_resolve_ambiguous_as_new_payment(send, auth):
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA on 12-11-26")
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at CAFE on 12-11-26", 1)
    send("VM-TESTCC", "TESTCARD ALERT: card XX9999 used for INR 20.00", 2)
    item = ReviewItem.objects.get()
    assert _post(f"/api/v1/review/{item.pk}/resolve", auth, {"entry_id": None}).status_code == 200
    assert LedgerEntry.objects.count() == 3


def test_post_an_unpaired_transfer_on_instruction(send, auth, firefly, django_capture_on_commit_callbacks):
    send("VM-TESTCC", "TESTCARD: payment of INR 7,000.00 received on card XX9999")
    sweep()
    item = ReviewItem.objects.get()
    with django_capture_on_commit_callbacks(execute=True):
        assert _post(f"/api/v1/review/{item.pk}/resolve", auth, {"post": True}).status_code == 200
    assert LedgerEntry.objects.get().status == "posted"
    assert len(firefly.transactions) == 1
