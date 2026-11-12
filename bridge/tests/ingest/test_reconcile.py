import pytest

from ingest.models import BalanceObservation, LedgerEntry, ParsedTransaction, ReviewItem

from .helpers import ingest

pytestmark = pytest.mark.django_db

ACC_A, ACC_B, CARD = "1", "2", "3"


def debit(amount="500.00", acct="1111", ref="111111111111", vpa="shop@upi", date="12-11-26"):
    return f"TESTBANK: INR {amount} debited from a/c XX{acct} to {vpa} on {date} ref {ref}"


def credit(amount="500.00", acct="2222", ref="111111111111", vpa="me@upi"):
    return f"TESTBANK: INR {amount} credited to a/c XX{acct} from {vpa} on 12-11-26 ref {ref}"


@pytest.fixture
def send(firefly, django_capture_on_commit_callbacks):
    def _send(sender, text, minutes=0):
        return ingest(django_capture_on_commit_callbacks, sender, text, minutes)
    return _send


def test_plain_upi_debit_becomes_a_withdrawal(send):
    send("VM-TESTBK", debit())
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.source_account_id, entry.amount_paise, entry.counterparty) == ("withdrawal", ACC_A, 50000, "shop@upi")
    assert entry.messages.count() == 1


def test_same_reference_twice_is_one_payment(send):
    send("VM-TESTBK", debit(), 0)
    send("VM-TESTBK", debit(), 5)  # bank resent the alert later
    assert LedgerEntry.objects.count() == 1
    assert LedgerEntry.objects.get().messages.count() == 2


def test_different_references_are_two_payments(send):
    send("VM-TESTBK", debit(ref="111111111111"))
    send("VM-TESTBK", debit(ref="222222222222"), 1)
    assert LedgerEntry.objects.count() == 2


def test_two_message_types_for_one_payment_merge_by_time_window(send):
    send("VM-TESTCC", "TESTCARD: INR 499.00 spent on card XX9999 at SHOP on 12-11-26")
    send("VM-TESTCC", "TESTCARD ALERT: card XX9999 used for INR 499.00", 3)
    assert LedgerEntry.objects.count() == 1


def test_same_message_type_twice_is_two_payments(send):
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA on 12-11-26")
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA STALL on 12-11-26", 2)
    assert LedgerEntry.objects.count() == 2


def test_outside_the_window_is_a_new_payment(send):
    send("VM-TESTCC", "TESTCARD: INR 499.00 spent on card XX9999 at SHOP on 12-11-26")
    send("VM-TESTCC", "TESTCARD ALERT: card XX9999 used for INR 499.00", 120)
    assert LedgerEntry.objects.count() == 2


def test_ambiguous_match_goes_to_review(send):
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA on 12-11-26")
    send("VM-TESTCC", "TESTCARD: INR 20.00 spent on card XX9999 at TEA STALL on 12-11-26", 1)
    send("VM-TESTCC", "TESTCARD ALERT: card XX9999 used for INR 20.00", 2)
    item = ReviewItem.objects.get()
    assert item.reason == "ambiguous_match" and len(item.candidates) == 2
    assert LedgerEntry.objects.count() == 2


def test_own_transfer_by_shared_reference_is_one_transfer(send):
    send("VM-TESTBK", debit(acct="1111", ref="333333333333"))
    send("VM-TESTBK", credit(acct="2222", ref="333333333333"), 1)
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.source_account_id, entry.destination_account_id) == ("transfer", ACC_A, ACC_B)
    assert entry.counterparty == "" and entry.messages.count() == 2


def test_credit_first_then_debit_is_still_one_transfer(send):
    send("VM-TESTBK", credit(acct="2222", ref="444444444444"))
    send("VM-TESTBK", debit(acct="1111", ref="444444444444"), 1)
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.source_account_id, entry.destination_account_id) == ("transfer", ACC_A, ACC_B)


def test_same_amount_without_shared_reference_is_not_a_transfer(send):
    send("VM-TESTBK", debit(acct="1111", ref="555555555555"))
    send("VM-TESTBK", credit(acct="2222", ref="666666666666"), 1)
    assert sorted(LedgerEntry.objects.values_list("type", flat=True)) == ["deposit", "withdrawal"]


def test_card_bill_payment_naming_the_card_is_a_transfer(send):
    send("VM-TESTBK", "TESTBANK: INR 5,000.00 paid from a/c XX1111 to card XX9999")
    send("VM-TESTCC", "TESTCARD: payment of INR 5,000.00 received on card XX9999", 30)
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.source_account_id, entry.destination_account_id) == ("transfer", ACC_A, CARD)
    assert entry.messages.count() == 2 and not entry.awaiting_partner


def test_card_bill_payment_pairs_without_card_digits(send):
    send("VM-TESTCC", "TESTCARD: payment of INR 7,000.00 received on card XX9999")
    entry = LedgerEntry.objects.get()
    assert entry.awaiting_partner  # never posted alone as income
    send("VM-TESTBK", "TESTBANK: INR 7,000.00 paid from a/c XX1111 to a credit card", 45)
    entry.refresh_from_db()
    assert (entry.type, entry.source_account_id, entry.destination_account_id) == ("transfer", ACC_A, CARD)
    assert not entry.awaiting_partner


def test_refund_is_a_deposit(send):
    send("VM-TESTCC", "TESTCARD: refund of INR 99.00 to card XX9999 from SHOP.")
    entry = LedgerEntry.objects.get()
    assert (entry.type, entry.destination_account_id, entry.counterparty) == ("deposit", CARD, "SHOP")


def test_reversal_before_posting_cancels_the_debit(send):
    send("VM-TESTBK", debit(ref="777777777777"))
    send("VM-TESTBK", "TESTBANK: INR 500.00 reversed to a/c XX1111 ref 777777777777", 10)
    entry = LedgerEntry.objects.get()
    assert entry.status == "cancelled" and entry.messages.count() == 2


def test_reversal_after_posting_is_a_deposit(send, firefly):
    from ingest.tasks import sweep

    send("VM-TESTBK", debit(ref="888888888888"))
    sweep()
    send("VM-TESTBK", "TESTBANK: INR 500.00 reversed to a/c XX1111 ref 888888888888", 10)
    reversal = LedgerEntry.objects.get(type="deposit")
    assert reversal.is_reversal and reversal.status == "pending"


def test_balance_in_a_transaction_sms_is_recorded(send):
    send("VM-TESTBK", debit() + ". Bal INR 12,000.50")
    obs = BalanceObservation.objects.get()
    assert (obs.firefly_account_id, obs.balance_paise) == (ACC_A, 1200050)


def test_balance_only_alert(send):
    from ingest.models import RawMessage

    send("VM-TESTBK", "TESTBANK: balance in a/c XX2222 is INR 1,00,000.00")
    assert BalanceObservation.objects.get().balance_paise == 10000000
    assert RawMessage.objects.get().status == "ignored"
    assert ParsedTransaction.objects.count() == 0 and LedgerEntry.objects.count() == 0


def test_every_entry_links_to_its_raw_messages(send):
    send("VM-TESTBK", debit())
    entry = LedgerEntry.objects.get()
    assert [m.raw.body for m in entry.messages.all()] == [debit()]


def test_money_from_an_own_upi_id_waits_for_its_other_half(send, settings):
    settings.INGEST_OWN_VPAS = {"me@upi"}
    send("VM-TESTBK", credit(acct="2222", ref="999999999999", vpa="ME@upi"))
    entry = LedgerEntry.objects.get()
    assert entry.awaiting_partner  # not income
    assert entry.messages.get().kind == "own_transfer"


def test_money_from_someone_else_is_income(send, settings):
    settings.INGEST_OWN_VPAS = {"me@upi"}
    send("VM-TESTBK", credit(acct="2222", ref="999999999999", vpa="friend@upi"))
    assert not LedgerEntry.objects.get().awaiting_partner
