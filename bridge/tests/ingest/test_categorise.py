"""Asking the owner for a category when a posted payment has none (M7 addition)."""
import datetime as dt

import pytest
from django.test import Client
from django.utils import timezone

from advisor import alerts
from ingest import categorise
from ingest.models import LedgerEntry, ReviewItem

pytestmark = pytest.mark.django_db

NOW = timezone.now()


@pytest.fixture
def ff(firefly):
    for name in ("Food & dining", "Groceries", "Family & friends"):
        firefly.categories.append({"id": str(len(firefly.categories) + 1), "attributes": {"name": name}})
    return firefly


def posted(gid, minutes_ago=30, counterparty="SHOP"):
    return LedgerEntry.objects.create(
        type=LedgerEntry.Type.WITHDRAWAL, status=LedgerEntry.Status.POSTED, amount_paise=25000,
        occurred_at=NOW, counterparty=counterparty, firefly_group_id=gid,
        posted_at=NOW - dt.timedelta(minutes=minutes_ago))


def _post(url, auth, data):
    return Client().post(url, data=data, content_type="application/json", **auth)


def test_asks_only_for_posted_payments_without_a_category(ff):
    posted(ff.add_withdrawal("Tea Stall", "250.00", tags=["ai:needs-review"]))
    posted(ff.add_withdrawal("Big Bazaar", "250.00", category="Groceries"))
    posted(ff.add_withdrawal("Just Now", "250.00"), minutes_ago=2)  # the AI categoriser still has time
    ff.add_withdrawal("Typed in Firefly", "250.00")  # not posted by the bridge
    posted(ff.add_withdrawal("Market value change", "250.00", tags=["valuation"]))
    assert categorise.check(NOW) == {"opened": 1, "closed": 0}
    item = ReviewItem.objects.get()
    assert item.reason == "category_needed" and item.suggestion["payee"] == "Tea Stall"
    assert item.suggestion["amount_paise"] == 25000 and item.suggestion["date"] == "2026-11-10"
    assert categorise.check(NOW) == {"opened": 0, "closed": 0}  # asked once only


def test_ignored_question_is_not_asked_again(ff, auth):
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    item = ReviewItem.objects.get()
    assert _post(f"/api/v1/review/{item.pk}/ignore", auth, {}).status_code == 200
    assert categorise.check(NOW)["opened"] == 0


def test_suggests_the_payees_past_categories(ff):
    ff.add_withdrawal("Tea Stall", "50.00", category="Food & dining")
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    assert ReviewItem.objects.get().suggestion["suggested"] == ["Food & dining"]


def test_choose_sets_category_and_removes_needs_review_tag(ff, auth):
    gid = ff.add_withdrawal("Tea Stall", "250.00", tags=["ai:needs-review", "bridge"])
    posted(gid)
    categorise.check(NOW)
    item = ReviewItem.objects.get()
    response = _post(f"/api/v1/review/{item.pk}/category", auth, {"category": "Food & dining", "always": False})
    assert response.status_code == 200 and response.json()["rule"] is None
    split = ff.groups[0]["attributes"]["transactions"][0]
    assert split["category_name"] == "Food & dining" and split["tags"] == ["bridge", "category-by-owner"]
    assert ff.rules == [] and ReviewItem.objects.get().status == "resolved"


def test_always_creates_one_rule_and_answers_the_same_payee(ff, auth):
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    posted(ff.add_withdrawal("Tea Stall", "30.00"))
    posted(ff.add_withdrawal("Other", "30.00"))
    categorise.check(NOW)
    first = ReviewItem.objects.filter(suggestion__payee="Tea Stall").order_by("pk").first()
    response = _post(f"/api/v1/review/{first.pk}/category", auth, {"category": "Food & dining", "always": True})
    assert response.status_code == 200 and len(response.json()["also_set"]) == 1
    assert len(ff.rule_groups) == 1 and len(ff.rules) == 1
    rule = ff.rules[0]["attributes"]
    assert {"type": "destination_account_is", "value": "Tea Stall", "active": True, "stop_processing": False} in rule["triggers"]
    assert rule["actions"][0]["value"] == "Food & dining"
    assert ReviewItem.objects.filter(status="open").count() == 1  # only "Other" is left
    # choosing again for the same payee updates the rule instead of adding a second one
    posted(ff.add_withdrawal("Tea Stall", "10.00"))
    categorise.check(NOW)
    third = ReviewItem.objects.get(status="open", suggestion__payee="Tea Stall")
    _post(f"/api/v1/review/{third.pk}/category", auth, {"category": "Groceries", "always": True})
    assert len(ff.rules) == 1 and ff.rules[0]["attributes"]["actions"][0]["value"] == "Groceries"


def test_unknown_category_and_bad_body_are_refused(ff, auth):
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    item = ReviewItem.objects.get()
    assert _post(f"/api/v1/review/{item.pk}/category", auth, {"category": "Made up"}).status_code == 400
    assert _post(f"/api/v1/review/{item.pk}/category", auth, {"category": "Groceries", "always": "yes"}).status_code == 400
    assert ff.groups[0]["attributes"]["transactions"][0]["category_name"] is None


def test_category_needs_the_token(ff):
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    item = ReviewItem.objects.get()
    assert Client().post(f"/api/v1/review/{item.pk}/category", {"category": "Groceries"},
                         content_type="application/json").status_code == 401


def test_closed_when_categorised_elsewhere(ff):
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    ff.groups[0]["attributes"]["transactions"][0]["category_name"] = "Food & dining"  # set in the categoriser page
    assert categorise.check(NOW) == {"opened": 0, "closed": 1}
    assert ReviewItem.objects.get().status == "resolved"


def test_alert_carries_the_choices(ff):
    ff.add_withdrawal("Tea Stall", "50.00", category="Food & dining")
    posted(ff.add_withdrawal("Tea Stall", "250.00"))
    categorise.check(NOW)
    found = [a for a in alerts.build(timezone.localdate(), ff.client()) if a["type"] == "category_needed"]
    assert len(found) == 1
    data = found[0]["data"]
    assert data["choices"] == ["Family & friends", "Food & dining", "Groceries"]
    assert data["suggested"] == ["Food & dining"] and data["payee"] == "Tea Stall" and data["amount_paise"] == 25000
    assert "₹250" in found[0]["message"]
    assert not any(a["type"] == "review_waiting" for a in alerts.build(timezone.localdate(), ff.client()))
