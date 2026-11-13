"""M5: EMI letters, card dues, goals, investments and net worth. Values are invented."""
import datetime as dt

import pytest
from django.test import Client

from ingest.models import ReviewItem
from ingest.tasks import build_payload
from mail.models import GmailAccount, StatementAttachment
from statements.parsers import axis_emi
from statements.parsers.common import CasDocument, Holding, StatementError
from statements.parsers.common import Statement
from tests.ingest.helpers import ingest
from wealth import apply, dues, goals, networth
from wealth.models import CardDue, CasStatement, EmiPlan, NetWorthSnapshot

pytestmark = pytest.mark.django_db
TODAY = dt.date(2026, 11, 14)

# Shaped like the owner's real Axis EMI letter (2026-11-14); every value invented.
EMI_LETTER = [
    """Ref. No.EMIT_00000000001234
Re: Conversion of Transaction into EMI
Card number : 5000XXXXXXXX9999
Date of Transaction : 07-OCT-26
Transaction Amount : Rs. 6000
Merchant Name : SHOP PAYMENTS CITY
Installment Amount(excluding taxes) : Rs. 2040
Interest Rate : 1.50 % p.m.
Tenure : 3 months
AXIS Bank Credit Card""",
    """Ref no : EMIT_00000000001234
00000000001234 0 13-OCT-26 0 0 10 6000 09-OCT-26
00000000001234 1 13-NOV-26 2040 1950 90 4050 09-OCT-26
00000000001234 2 13-DEC-26 2040 1990 50 2060 09-OCT-26
00000000001234 3 13-JAN-27 2040 2061 21 0 09-OCT-26""",
]


def attachment(key="axis-card", name="x.pdf"):
    account, _ = GmailAccount.objects.get_or_create(tag="t", defaults={"token_encrypted": "x"})
    return StatementAttachment.objects.create(account=account, gmail_message_id=name, attachment_id="a", filename=name, key=key)


def test_emi_letter_parses_schedule_within_rounding():
    letter = axis_emi.parse(EMI_LETTER)
    assert (letter.account_digits, letter.reference_tail, letter.principal_paise) == ("9999", "1234", 600000)
    assert [i.emi_paise for i in letter.instalments] == [0, 204000, 204000, 204000]
    assert letter.instalments[1].date == dt.date(2026, 11, 13)
    assert "1234" not in letter.merchant and letter.rate_text == "1.50 % p.m."


def test_emi_letter_that_does_not_add_up_is_refused():
    broken = [EMI_LETTER[0].replace("Rs. 6000", "Rs. 9000"), EMI_LETTER[1]]
    with pytest.raises(StatementError):
        axis_emi.parse(broken)


def test_emi_letter_becomes_plan_and_one_firefly_bill(firefly):
    att = attachment()
    result = apply.apply_document(att, axis_emi.parse(EMI_LETTER))
    assert "EMI plan" in result
    plan = EmiPlan.objects.get()
    assert plan.firefly_account_id == "3" and plan.name.startswith("EMI: Shop Payments City (Card C)")
    bill = firefly.bills[0]["attributes"]
    assert (bill["amount_max"], bill["date"], bill["end_date"], bill["repeat_freq"]) == ("2040.00", "2026-11-13", "2027-01-13", "monthly")
    apply.apply_document(att, axis_emi.parse(EMI_LETTER))  # again: updated, not duplicated
    assert EmiPlan.objects.count() == 1 and len(firefly.bills) == 1


def test_upcoming_lists_emis_and_card_dues(firefly):
    att = attachment()
    apply.apply_document(att, axis_emi.parse(EMI_LETTER))
    due_att = attachment(name="s.pdf")
    st = Statement(kind="card", account_digits="9999", period_start=None, period_end=dt.date(2026, 11, 10),
                   closing_paise=9900, total_due_paise=9900, minimum_due_paise=500, due_date=dt.date(2026, 11, 30))
    apply.record_card_due(due_att, st, "3")
    items = dues.upcoming(45, today=TODAY)
    assert [(i["type"], i["date"], i["amount_paise"]) for i in items] == [
        ("card_due", "2026-11-30", 9900), ("emi", "2026-12-13", 204000)]
    assert items[1]["instalments_left"] == 2


def card_due(minimum=500, statement=dt.date(2026, 11, 10), due=dt.date(2026, 11, 12)):
    st = Statement(kind="card", account_digits="9999", period_start=None, period_end=statement,
                   closing_paise=9900, total_due_paise=9900, minimum_due_paise=minimum, due_date=due)
    return apply.record_card_due(attachment(name=f"{statement}{minimum}.pdf"), st, "3")


def test_unpaid_due_goes_to_review(firefly):
    card_due()
    assert dues.check_dues(TODAY) == {"paid": 0, "unpaid": 1}
    assert ReviewItem.objects.get().reason == "card_due_unpaid"
    assert CardDue.objects.get().status == "unpaid"


def test_paid_due_is_closed_and_payment_counted_once(firefly, django_capture_on_commit_callbacks):
    card_due(statement=dt.date(2026, 11, 11), due=dt.date(2026, 11, 13))
    # Bank side and card side of one bill payment: one transfer, counted once.
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK", "TESTBANK: INR 600.00 paid from a/c XX1111 to card XX9999")
    ingest(django_capture_on_commit_callbacks, "VM-TESTCC", "TESTCARD: payment of INR 600.00 received on card XX9999", minutes=2)
    assert dues.check_dues(TODAY) == {"paid": 1, "unpaid": 0}
    assert CardDue.objects.get().paid_paise == 60000


def test_dues_from_before_the_ledger_start_are_not_judged(firefly):
    card_due(statement=dt.date(2026, 10, 13), due=dt.date(2026, 11, 2))
    assert dues.check_dues(TODAY) == {"paid": 0, "unpaid": 0}
    assert ReviewItem.objects.count() == 0


def test_networth_counts_card_dues_and_loans_as_liabilities_and_no_limit(firefly):
    firefly.accounts[0]["attributes"]["current_balance"] = "1000.00"
    firefly.accounts[2]["attributes"]["current_balance"] = "-250.50"  # card: owed
    firefly.add(name="Bike loan", type="liabilities", liability_type="loan", current_balance="-500.00", active=True)
    firefly.add(name="Old card", type="asset", account_role="ccAsset", current_balance="0", active=False)
    result = networth.compute(client=firefly.client())
    assert (result["assets_paise"], result["liabilities_paise"], result["net_worth_paise"]) == (100000, 75050, 24950)
    assert "Old card" not in [a["name"] for a in result["accounts"]]


def test_snapshot_once_per_date(firefly):
    networth.snapshot(dt.date(2026, 11, 30), client=firefly.client())
    networth.snapshot(dt.date(2026, 11, 30), client=firefly.client())
    assert NetWorthSnapshot.objects.count() == 1
    assert networth.last_month_end(dt.date(2026, 12, 1)) == dt.date(2026, 11, 30)


def test_goal_progress_comes_from_linked_account_capped_at_target(firefly):
    firefly.accounts[1]["attributes"]["current_balance"] = "300000.00"
    doc = {"goals": [{"name": "Bike", "target": "250000.00", "target_date": "2026-12-15", "accounts": ["Bank B"]}]}
    planned = goals.plan(doc, firefly.client(), TODAY)
    assert goals.sync(planned, firefly.client()) == [("Bike", "created")]
    piggy = firefly.piggy_banks[0]["attributes"]
    assert piggy["target_amount"] == "250000.00" and piggy["accounts"] == [{"account_id": "2", "current_amount": "250000.00"}]
    assert goals.sync(planned, firefly.client()) == [("Bike", "updated")] and len(firefly.piggy_banks) == 1


def test_goal_needed_per_month():
    class C:
        def list_all(self, path):
            return [{"id": "1", "attributes": {"name": "Bike", "target_amount": "250000.00", "current_amount": "50000.00",
                                                "target_date": "2026-12-15T00:00:00+05:30"}}]
    row = goals.progress(TODAY, C())[0]
    assert (row["left_paise"], row["percent"], row["needed_per_month_paise"]) == (20000000, 20, 10000000)


def test_goal_errors_are_clear(firefly):
    with pytest.raises(goals.GoalError, match="quoted amount"):
        goals.plan({"goals": [{"name": "X", "target": 100, "accounts": ["Bank A"]}]}, firefly.client(), TODAY)
    with pytest.raises(goals.GoalError, match="no Firefly asset account"):
        goals.plan({"goals": [{"name": "X", "target": "100.00", "accounts": ["Nope"]}]}, firefly.client(), TODAY)
    with pytest.raises(goals.GoalError, match="no spending recorded"):
        goals.plan({"goals": [{"name": "E", "months_of_spend": 6, "accounts": ["Bank A"]}]}, firefly.client(), TODAY)


def test_emergency_fund_from_spend_leaves_out_revaluations(firefly):
    firefly.expenses = [("Shop", "60000.00"), ("Market value change", "99999.00")]
    planned = goals.plan({"goals": [{"name": "E", "months_of_spend": 3, "accounts": ["Bank A"]}]}, firefly.client(), TODAY)
    assert planned[0]["target_paise"] == 6000000 // 6 * 3


def cas(total=1500000):
    return CasDocument(statement_date=dt.date(2026, 11, 30), total_paise=total, holdings=[
        Holding("mutual_fund", "INF000000001", "Some Flexi Cap Fund", "10.123", "123.4567", 1000000),
        Holding("stock", "INE000000001", "SOME COMPANY LTD", "5", "1000.00", 500000)])


def test_cas_creates_investment_accounts_and_revalues_once(firefly):
    result = apply.apply_document(attachment("cdsl"), cas())
    names = [a["attributes"]["name"] for a in firefly.accounts]
    assert "Mutual funds (CAS)" in names and "Demat stocks (CAS)" in names
    vals = [t["transactions"][0] for t in firefly.transactions]
    assert sorted((v["type"], v["amount"]) for v in vals) == [("deposit", "10000.00"), ("deposit", "5000.00")]
    assert all("valuation" in v["tags"] for v in vals) and "adjusted" in result
    assert CasStatement.objects.get().holdings.count() == 2


def test_cas_that_does_not_add_up_is_refused(firefly):
    with pytest.raises(ValueError):
        apply.apply_document(attachment("cdsl"), cas(total=1))


def test_older_cas_does_not_override_a_newer_value(firefly):
    apply.apply_document(attachment("cdsl", "new.pdf"), cas())
    older = cas()
    older.statement_date = dt.date(2026, 10, 31)
    result = apply.apply_document(attachment("cdsl", "old.pdf"), older)
    assert "a newer CAS sets the value" in result and len(firefly.transactions) == 2


def test_sip_debit_is_a_transfer_into_investments_once_the_account_exists(firefly, django_capture_on_commit_callbacks, settings):
    from django.core.cache import cache

    settings.INVESTMENT_PAYEE_REGEX = r"^mfund@"
    ingest(django_capture_on_commit_callbacks, "VM-TESTBK",
           "TESTBANK: INR 1000.00 debited from a/c XX1111 to mfund@icici on 12-11-26 ref 222222222222")
    from ingest.models import LedgerEntry
    entry = LedgerEntry.objects.get()
    assert build_payload(entry)["transactions"][0]["type"] == "withdrawal"  # no investments account yet
    firefly.add(name="Mutual funds (CAS)", type="asset", account_role="savingAsset", active=True)
    cache.delete("wealth:mf-account-id")
    tx = build_payload(entry)["transactions"][0]
    assert (tx["type"], tx["destination_id"], tx["source_id"]) == ("transfer", "4", "1")
    assert "category_name" not in tx and "investment" in tx["tags"]


def test_document_profiles_cannot_create_transactions(tmp_path, settings):
    from ingest import parser

    (tmp_path / "doc.yaml").write_text("id: d\naccount_kind: document\nsenders: [x.com]\npatterns:\n"
                                       "  - id: t\n    direction: debit\n    match: '(?P<amount>\\d+) (?P<account>\\d{4})'\n")
    settings.INGEST_EMAIL_PROFILE_DIRS = [tmp_path]
    parser.clear_cache()
    with pytest.raises(parser.ProfileError, match="document profiles"):
        parser.profiles("email")


@pytest.mark.parametrize("path", ["networth", "upcoming", "goals", "holdings"])
def test_new_endpoints_need_the_token_and_are_read_only(firefly, auth, path):
    assert Client().get(f"/api/v1/{path}").status_code in (401, 403)
    assert Client().get(f"/api/v1/{path}", **auth).status_code == 200
    assert Client().post(f"/api/v1/{path}", **auth).status_code == 405
