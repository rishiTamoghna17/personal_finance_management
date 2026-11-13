import io

import pytest
from django.core.management import call_command

from firefly.management.commands import seed_categories
from firefly.client import FireflyClient

YAML = 'categories:\n  - {name: "Food & dining", notes: "Zomato, Swiggy"}\n  - {name: "Cash", notes: "ATM"}\n'


def test_seed_categories_creates_then_updates_notes(tmp_path, monkeypatch, firefly):
    path = tmp_path / "c.yaml"
    path.write_text(YAML)
    out = io.StringIO()
    call_command("seed_categories", str(path), stdout=out)
    assert out.getvalue().count("created") == 2
    path.write_text(YAML.replace("ATM", "ATM cash"))
    out = io.StringIO()
    call_command("seed_categories", str(path), stdout=out)
    assert "updated  Cash" in out.getvalue() and "exists   Food & dining" in out.getvalue()
    assert {c["attributes"]["name"] for c in firefly.categories} == {"Food & dining", "Cash"}


def test_setup_categorizer_creates_one_internal_webhook(firefly):
    call_command("setup_categorizer", stdout=io.StringIO())
    call_command("setup_categorizer", stdout=io.StringIO())
    assert len(firefly.webhooks) == 1
    hook = firefly.webhooks[0]["attributes"]
    assert hook["url"] == "http://categorizer:3000/webhook" and hook["triggers"] == ["STORE_TRANSACTION"]


@pytest.mark.django_db
def test_known_category_is_sent_to_firefly(firefly, django_capture_on_commit_callbacks):
    from ingest.tasks import sweep
    from mail import tasks as mail_tasks
    from mail.models import GmailAccount
    from core.crypto import encrypt
    from tests.mail.test_mail import message

    account = GmailAccount.objects.create(tag="a", token_encrypted=encrypt("{}"))
    text = ("Dear Sir / Madam, We have credited your account XXXXXXXX2222 with Rs 26667.00 (Rupees ...) through payment "
            "reference number 1000000001 on behalf of EMPLOYER LLP. Regards, ICICI Bank Limited")
    with django_capture_on_commit_callbacks(execute=True):
        mail_tasks.ingest_message(account, message("s1", "ICICI Bank E-Payment for M/s NAME", text, sender="ICICI <e@icicibank.com>"))
    sweep()
    tx = firefly.transactions[0]["transactions"][0]
    assert (tx["type"], tx["category_name"], tx["destination_id"]) == ("deposit", "Salary", "2")
