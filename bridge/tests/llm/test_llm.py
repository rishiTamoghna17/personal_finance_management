import datetime as dt
import json

import httpx
import pytest
from django.test import Client

from ingest.models import LedgerEntry, RawMessage, ReviewItem
from llm import fallback, masking, providers
from llm.tasks import suggest_for_review
from tests.ingest.helpers import BASE, ingest

pytestmark = pytest.mark.django_db
SMS = "Rs.250.00 sent from A/c XX1111 to rahul.k@okaxis on 12-11-26 UPI Ref 123456789012 call 18001234567"


def test_mask_hides_upi_ids_and_long_numbers_but_keeps_amounts_and_masked_digits():
    masked, mapping = masking.mask(SMS)
    assert "rahul.k@okaxis" not in masked and "123456789012" not in masked and "18001234567" not in masked
    assert "Rs.250.00" in masked and "XX1111" in masked and "12-11-26" in masked
    assert masking.unmask("<VPA1> <REF1>", mapping) == "rahul.k@okaxis 123456789012"


def test_names_are_masked_only_for_cloud_providers():
    text = "INR 99.00 is paid from HSBC account XXXXXX1111 to Rahul Kumar Sharma on 12-Nov-26"
    assert "Rahul Kumar Sharma" in masking.mask(text)[0]
    masked, _ = masking.mask(text, names=True)
    assert "Rahul Kumar Sharma" not in masked and "HSBC" in masked


GOOD = {"is_transaction": True, "amount": "250.00", "direction": "debit", "account_digits": "XX1111",
        "date": "2026-11-12", "counterparty": "rahul.k@okaxis", "reference": "123456789012"}


def test_check_accepts_a_faithful_reading():
    s = fallback.check(GOOD, SMS, BASE)
    assert (s["amount_paise"], s["direction"], s["account_last4"], s["reference"]) == (25000, "debit", "1111", "123456789012")


@pytest.mark.parametrize("change,reason", [
    ({"is_transaction": False}, "not a transaction"),
    ({"amount": "2500.00"}, "amount does not appear"),
    ({"amount": "abc"}, "not a number"),
    ({"direction": "sideways"}, "direction"),
    ({"account_digits": "XX9999"}, "account digits"),
    ({"date": "2026-10-01"}, "more than 7 days"),
])
def test_check_rejects_invented_values(change, reason):
    with pytest.raises(fallback.Rejected, match=reason):
        fallback.check({**GOOD, **change}, SMS, BASE)


def capture_transport(answer, seen):
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": json.dumps(answer)}})
    return httpx.MockTransport(handler)


def test_ollama_request_carries_no_upi_id_or_reference(monkeypatch):
    seen = []
    real_post = providers._post
    monkeypatch.setattr(providers, "_post", lambda url, payload, headers=None, transport=None:
                        real_post(url, payload, headers, capture_transport(
                            {**GOOD, "counterparty": "<VPA1>", "reference": "<REF1>"}, seen)))

    class Raw:
        body, sent_at = SMS, BASE
    s = fallback.suggest(Raw())
    sent = json.dumps(seen[0])
    assert "rahul.k@okaxis" not in sent and "123456789012" not in sent and "18001234567" not in sent
    assert seen[0]["model"] and seen[0]["format"] == "json"
    assert (s["counterparty"], s["reference"]) == ("rahul.k@okaxis", "123456789012")  # put back locally


@pytest.mark.parametrize("provider,body", [
    ("groq", {"choices": [{"message": {"content": json.dumps(GOOD)}}]}),
    ("gemini", {"candidates": [{"content": {"parts": [{"text": json.dumps(GOOD)}]}}]}),
])
def test_cloud_providers(settings, provider, body):
    settings.LLM_PROVIDER, settings.LLM_API_KEY = provider, "test-key"
    headers = []
    transport = httpx.MockTransport(lambda r: headers.append(dict(r.headers)) or httpx.Response(200, json=body))
    assert providers.ask("s", "u", transport=transport)["amount"] == "250.00"
    assert "test-key" in json.dumps(headers) and "key=" not in str(headers)  # key in a header, not the URL


def test_unparsed_bank_sms_gets_a_suggestion_that_can_be_accepted(firefly, settings, monkeypatch, auth, django_capture_on_commit_callbacks):
    settings.LLM_FALLBACK_ENABLED = True
    monkeypatch.setattr(providers, "ask", lambda system, user, transport=None: {
        "is_transaction": True, "amount": "75.00", "direction": "debit", "account_digits": "XX1111",
        "date": None, "counterparty": "TEA STALL", "reference": None})
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: a new kind of message, INR 75.00 gone from XX1111 to TEA STALL")
    item = ReviewItem.objects.get()
    assert item.reason == "unparsed" and item.suggestion["status"] == "ok" and item.suggestion["amount_paise"] == 7500
    assert LedgerEntry.objects.count() == 0  # a suggestion never posts by itself
    response = Client().post(f"/api/v1/review/{item.pk}/accept", data={}, content_type="application/json", **auth)
    assert response.status_code == 200
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.amount_paise, entry.source_account_id) == ("withdrawal", 7500, "1")


def test_unknown_sender_is_never_sent_to_the_model(firefly, settings, monkeypatch, django_capture_on_commit_callbacks):
    settings.LLM_FALLBACK_ENABLED = True
    calls = []
    monkeypatch.setattr(providers, "ask", lambda *a, **k: calls.append(a) or GOOD)
    ingest(django_capture_on_commit_callbacks, "VM-FRIEND", "Lunch tomorrow? I owe you Rs 250")
    assert calls == [] and ReviewItem.objects.get().suggestion == {}


def test_rejected_reading_is_recorded_not_posted(firefly, settings, monkeypatch, django_capture_on_commit_callbacks):
    settings.LLM_FALLBACK_ENABLED = True
    monkeypatch.setattr(providers, "ask", lambda *a, **k: {**GOOD, "amount": "9999.00"})
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: a new kind of message, INR 75.00 gone from XX1111")
    assert ReviewItem.objects.get().suggestion == {"status": "rejected", "reason": "amount does not appear in the message"}
    assert LedgerEntry.objects.count() == 0
