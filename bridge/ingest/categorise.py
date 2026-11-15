"""Ask the owner for a category when a posted payment has none (M7 addition, approved 2026-11-15).

A few minutes after the bridge posts a withdrawal, the AI categoriser has had its chance. If Firefly still shows no
category, a `category_needed` review item is opened; the alert (later a phone notification) offers the owner's
categories. The answer sets the category in Firefly and, if asked, a Firefly rule so that payee is never asked again.
Only ledger records change (a category, a tag, a rule); nothing here can move money (rule 2).
"""
import datetime as dt
import logging
from collections import Counter

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from firefly.client import FireflyClient, FireflyError
from core.money import to_paise

from .models import LedgerEntry, ReviewItem

log = logging.getLogger(__name__)

WAIT_MINUTES = 10  # give the AI categoriser time to answer first
RULE_GROUP = "Payee categories (bridge)"
NEEDS_REVIEW_TAG = "ai:needs-review"
OWNER_TAG = "category-by-owner"


class CategoryError(Exception):
    pass


def _withdrawals(client, since):
    """[(group id, split)] for every withdrawal since a date."""
    out, page = [], 1
    while True:
        body = client._request("GET", "transactions", params={"type": "withdrawal", "start": since.isoformat(),
                                                               "page": page, "limit": 50})
        for group in body.get("data", []):
            for split in group["attributes"]["transactions"]:
                out.append((str(group["id"]), split))
        if page >= int(body.get("meta", {}).get("pagination", {}).get("total_pages", 1)):
            return out
        page += 1


def category_names(client):
    return sorted(c["attributes"]["name"] for c in client.list_all("categories"))


def _past_categories(splits):
    """{payee: [most used categories, best first]} from payments that already have one."""
    seen = {}
    for _, split in splits:
        if split.get("category_name"):
            seen.setdefault(split.get("destination_name", ""), Counter())[split["category_name"]] += 1
    return {payee: [name for name, _ in counts.most_common(3)] for payee, counts in seen.items()}


def check(now=None, client=None):
    """Every few minutes (Celery): open an item for each bridge-posted withdrawal without a category, and close
    open items whose payment got a category elsewhere (Firefly, the categoriser page or a rule)."""
    now = now or timezone.now()
    client = client or FireflyClient.from_settings()
    since = dt.date.fromisoformat(settings.INGEST_LEDGER_START)
    splits = _withdrawals(client, since)
    by_group = {gid: split for gid, split in splits}
    past = _past_categories(splits)
    entries = {e.firefly_group_id: e for e in LedgerEntry.objects.filter(
        status=LedgerEntry.Status.POSTED, type=LedgerEntry.Type.WITHDRAWAL, firefly_group_id__in=list(by_group),
        posted_at__lte=now - dt.timedelta(minutes=WAIT_MINUTES))}
    asked = set(ReviewItem.objects.filter(reason=ReviewItem.Reason.CATEGORY_NEEDED).values_list("entry_id", flat=True))
    opened = closed = 0
    for gid, entry in entries.items():
        split = by_group[gid]
        if split.get("category_name") or entry.pk in asked or "valuation" in (split.get("tags") or []):
            continue
        payee = split.get("destination_name", "") or entry.counterparty
        ReviewItem.objects.create(
            entry=entry, reason=ReviewItem.Reason.CATEGORY_NEEDED, detail=payee[:300],
            suggestion={"kind": "category", "group_id": gid, "journal_id": str(split.get("transaction_journal_id", "")),
                        "payee": payee, "amount_paise": abs(to_paise(split["amount"])),
                        "date": split["date"][:10], "account": split.get("source_name", ""),
                        "suggested": past.get(payee, [])})
        opened += 1
    for item in ReviewItem.objects.filter(reason=ReviewItem.Reason.CATEGORY_NEEDED, status=ReviewItem.Status.OPEN):
        split = by_group.get(item.suggestion.get("group_id"))
        if split and split.get("category_name"):
            _close(item, f"categorised elsewhere: {split['category_name']}", now)
            closed += 1
    if opened or closed:
        log.info("category check: %s asked, %s closed", opened, closed)
    return {"opened": opened, "closed": closed}


def _close(item, resolution, now=None):
    item.status, item.resolution, item.resolved_at = ReviewItem.Status.RESOLVED, resolution[:200], now or timezone.now()
    item.save(update_fields=["status", "resolution", "resolved_at"])


def _set_on_transaction(client, item, name):
    gid, jid = item.suggestion["group_id"], item.suggestion["journal_id"]
    split = client._request("GET", f"transactions/{gid}")["data"]["attributes"]["transactions"][0]
    tags = [t for t in (split.get("tags") or []) if t != NEEDS_REVIEW_TAG]
    if OWNER_TAG not in tags:
        tags.append(OWNER_TAG)
    client._request("PUT", f"transactions/{gid}", json={
        "apply_rules": False, "fire_webhooks": False,
        "transactions": [{"transaction_journal_id": jid, "category_name": name, "tags": tags}]})


def _rule_group_id(client):
    for group in client.list_all("rule-groups"):
        if group["attributes"]["title"] == RULE_GROUP:
            return str(group["id"])
    return str(client._request("POST", "rule-groups", json={
        "title": RULE_GROUP, "description": "Created by the bridge when you choose a category for a payee.",
        "active": True})["data"]["id"])


def _ensure_rule(client, payee, name):
    """One Firefly rule per payee: withdrawals to this payee get this category. An existing rule is updated."""
    title = f"Category for {payee}"[:255]
    body = {"title": title, "rule_group_id": _rule_group_id(client), "trigger": "store-journal", "active": True,
            "strict": True, "stop_processing": False,
            "triggers": [{"type": "transaction_type", "value": "withdrawal", "active": True, "stop_processing": False},
                         {"type": "destination_account_is", "value": payee, "active": True, "stop_processing": False}],
            "actions": [{"type": "set_category", "value": name, "active": True, "stop_processing": False}]}
    for rule in client.list_all("rules"):
        if rule["attributes"]["title"] == title:
            client._request("PUT", f"rules/{rule['id']}", json=body)
            return str(rule["id"])
    return str(client._request("POST", "rules", json=body)["data"]["id"])


def choose(item, name, always, client=None):
    """The owner picked a category. Returns {"category", "rule", "also_set": [review ids closed with it]}."""
    if item.reason != ReviewItem.Reason.CATEGORY_NEEDED or item.status != ReviewItem.Status.OPEN:
        raise CategoryError("this item is not an open category question")
    client = client or FireflyClient.from_settings()
    names = category_names(client)
    if name not in names:
        raise CategoryError("unknown category; pick one of your Firefly categories")
    try:
        _set_on_transaction(client, item, name)
        rule = None
        also = []
        payee = item.suggestion.get("payee", "")
        if always and payee:
            rule = _ensure_rule(client, payee, name)
            others = ReviewItem.objects.filter(reason=ReviewItem.Reason.CATEGORY_NEEDED, status=ReviewItem.Status.OPEN,
                                               suggestion__payee=payee).exclude(pk=item.pk)
            for other in others:
                _set_on_transaction(client, other, name)
                _close(other, f"category {name} (same payee)")
                also.append(other.pk)
    except FireflyError as exc:
        raise CategoryError(f"Firefly refused the change: {exc}") from None
    with transaction.atomic():
        _close(item, f"category {name}" + (" (always for this payee)" if rule else ""))
    return {"category": name, "rule": rule, "also_set": also}


def alerts():
    """One alert per open question, with the choices, for the app's notification."""
    items = ReviewItem.objects.filter(reason=ReviewItem.Reason.CATEGORY_NEEDED, status=ReviewItem.Status.OPEN)
    if not items:
        return []
    try:
        names = category_names(FireflyClient.from_settings())
    except FireflyError:
        names = []
    from advisor.render import inr

    out = []
    for item in items.order_by("created_at"):
        s = item.suggestion
        out.append({"type": "category_needed", "severity": "low",
                    "message": f"Which category is {inr(s['amount_paise'])} to {s['payee']} on {s['date']}?",
                    "data": {"review_id": item.pk, "payee": s["payee"], "amount_paise": s["amount_paise"],
                             "date": s["date"], "account": s["account"], "suggested": s.get("suggested", []),
                             "choices": names,
                             "answer": f"POST /api/v1/review/{item.pk}/category "
                                       '{"category": "<name>", "always": true|false}'}})
    return out
