"""Apply M5 documents: EMI letters -> EmiPlan + Firefly bill; CAS -> holdings + investment account valuation;
card statements -> CardDue. Every amount is integer paise; Firefly gets decimal strings."""
import datetime as dt
import logging

from django.conf import settings
from django.db import transaction

from core.money import to_decimal_string, to_paise
from firefly.client import FireflyClient
from ingest import accounts
from statements.parsers.common import CasDocument, EmiLetter

from .models import CardDue, CasStatement, EmiPlan, Holding

log = logging.getLogger(__name__)


def apply_document(att, document):
    if isinstance(document, EmiLetter):
        return apply_emi_letter(att, document)
    if isinstance(document, CasDocument):
        return apply_cas(att, document)
    raise TypeError(f"unknown document {type(document).__name__}")


# --- card dues -----------------------------------------------------------------------------------------------
def record_card_due(att, statement, account_id):
    """Called from statements.reconcile for card statements that print a due date."""
    if statement.kind != "card" or not statement.due_date or statement.total_due_paise is None:
        return None
    due, _ = CardDue.objects.update_or_create(
        attachment=att,
        defaults={"firefly_account_id": account_id, "statement_date": statement.period_end,
                  "due_date": statement.due_date, "total_due_paise": statement.total_due_paise,
                  "minimum_due_paise": statement.minimum_due_paise},
    )
    if due.total_due_paise <= 0 and due.status == CardDue.Status.OPEN:
        due.status = CardDue.Status.PAID
        due.save(update_fields=["status"])
    return due


# --- EMI letters -----------------------------------------------------------------------------------------------
def schedule_json(instalments):
    return [{"number": i.number, "date": i.date.isoformat(), "emi_paise": i.emi_paise,
             "principal_paise": i.principal_paise, "interest_paise": i.interest_paise} for i in instalments]


def bill_payload(plan):
    rows = [r for r in plan.schedule if r["emi_paise"] > 0]
    amount = to_decimal_string(max(r["emi_paise"] for r in rows))
    low = to_decimal_string(min(r["emi_paise"] for r in rows))
    return {
        "name": plan.name[:255], "amount_min": low, "amount_max": amount, "currency_code": "INR",
        "date": rows[0]["date"], "end_date": rows[-1]["date"], "repeat_freq": "monthly", "skip": 0, "active": True,
        "notes": f"Created by the bridge from {plan.source}. Interest {plan.rate_text or 'not stated'}. "
                 f"{len(rows)} instalments; EMI is billed on the card statement.",
    }


def sync_bill(plan, client=None):
    rows = [r for r in plan.schedule if r["emi_paise"] > 0]
    if not rows:
        return
    client = client or FireflyClient.from_settings()
    payload = bill_payload(plan)
    if plan.firefly_bill_id:
        client.update_bill(plan.firefly_bill_id, payload)
        return
    existing = {b["attributes"].get("name"): str(b["id"]) for b in client.list_all("bills")}
    bill_id = existing.get(payload["name"]) or str(client.create_bill(payload)["id"])
    EmiPlan.objects.filter(pk=plan.pk).update(firefly_bill_id=bill_id)
    plan.firefly_bill_id = bill_id


def apply_emi_letter(att, letter):
    account, why = accounts.resolve(letter.account_digits)
    if account is None:
        return f"EMI letter: account not found ({why})"
    name = f"EMI: {letter.merchant.title()} ({account.name})"
    if letter.reference_tail:
        name = f"{name} #{letter.reference_tail}"
    with transaction.atomic():
        plan, _ = EmiPlan.objects.update_or_create(
            attachment=att,
            defaults={"source": "axis-emi-letter", "firefly_account_id": account.id, "name": name[:160],
                      "reference_tail": letter.reference_tail, "principal_paise": letter.principal_paise,
                      "rate_text": letter.rate_text, "schedule": schedule_json(letter.instalments)},
        )
    sync_bill(plan)
    return f"EMI plan {plan.pk}: {len(letter.instalments)} rows, bill {plan.firefly_bill_id}"


# --- CAS: holdings and valuation -----------------------------------------------------------------------------
def ensure_investment_accounts(client):
    """The two investment asset accounts, created on first use. Returns {kind: account id}."""
    have = {a["attributes"].get("name"): str(a["id"]) for a in client.list_accounts("asset")}
    ids = {}
    for kind, name in settings.INVESTMENT_ACCOUNTS.items():
        if name not in have:
            created = client.create_account({
                "name": name, "type": "asset", "account_role": "savingAsset", "currency_code": "INR",
                "active": True, "include_net_worth": True,
                "notes": "Value as stated by the latest CDSL CAS. SIP debits are transfers into this account.",
            })
            have[name] = str(created["id"])
        ids[kind] = have[name]
    return ids


def valuation_payload(account_id, on_date, difference_paise, external_id):
    """One transaction that moves the account from its ledger balance to the CAS value on that date."""
    tx = {
        "date": dt.datetime.combine(on_date, dt.time(23, 0)).isoformat(),
        "amount": to_decimal_string(abs(difference_paise)), "currency_code": "INR",
        "description": "Market value as per CDSL CAS", "external_id": external_id,
        "tags": ["bridge", "valuation"], "notes": "Revaluation to the value stated in the CAS (not income or spending).",
    }
    if difference_paise > 0:
        tx.update(type="deposit", source_name=settings.VALUATION_COUNTERPARTY, destination_id=account_id)
    else:
        tx.update(type="withdrawal", source_id=account_id, destination_name=settings.VALUATION_COUNTERPARTY)
    return {"error_if_duplicate_hash": True, "apply_rules": False, "fire_webhooks": False, "transactions": [tx]}


def apply_cas(att, document):
    if sum(h.value_paise for h in document.holdings) != document.total_paise:
        raise ValueError("CAS holdings do not add up to the stated total")
    with transaction.atomic():
        cas, created = CasStatement.objects.get_or_create(
            attachment=att, defaults={"statement_date": document.statement_date, "total_paise": document.total_paise})
        if created:
            Holding.objects.bulk_create([
                Holding(cas=cas, kind=h.kind, isin=h.isin, name=h.name[:200], units=h.units, price=h.price,
                        value_paise=h.value_paise) for h in document.holdings])
    newer = CasStatement.objects.filter(statement_date__gt=cas.statement_date, applied_to_firefly=True).exists()
    if cas.applied_to_firefly or newer:
        return f"CAS {cas.statement_date}: {len(document.holdings)} holdings stored (a newer CAS sets the value)"
    return revalue(cas)


def revalue(cas, client=None):
    client = client or FireflyClient.from_settings()
    ids = ensure_investment_accounts(client)
    by_kind = {}
    for h in cas.holdings.all():
        kind = h.kind if h.kind in ids else "stock"
        by_kind[kind] = by_kind.get(kind, 0) + h.value_paise
    parts = []
    for kind, account_id in ids.items():
        target = by_kind.get(kind, 0)
        ledger = to_paise(client.get_account(account_id, cas.statement_date)["attributes"].get("current_balance") or "0")
        difference = target - ledger
        if difference:
            client.create_transaction(valuation_payload(account_id, cas.statement_date, difference,
                                                        f"cas-{cas.pk}-{kind}"))
        parts.append(f"{kind} {to_decimal_string(target)} (adjusted {to_decimal_string(difference)})")
    CasStatement.objects.filter(pk=cas.pk).update(applied_to_firefly=True)
    accounts._directory(refresh=True)
    return f"CAS {cas.statement_date}: " + "; ".join(parts)
