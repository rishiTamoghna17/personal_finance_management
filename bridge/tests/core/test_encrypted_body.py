"""M7: bank message bodies are encrypted in the database and read back as text."""
import datetime as dt

import pytest
from django.db import connection

from ingest.models import RawMessage

pytestmark = pytest.mark.django_db


def stored_text(pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT body FROM ingest_rawmessage WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def test_body_is_encrypted_at_rest_and_readable_by_the_bridge():
    raw = RawMessage.objects.create(source="sms", sender="VM-TESTBK", header="TESTBK", content_hash="h1",
                                    body="INR 500.00 debited from a/c XX1111", sent_at=dt.datetime.now(dt.timezone.utc))
    on_disk = stored_text(raw.pk)
    assert on_disk.startswith("enc1:") and "XX1111" not in on_disk and "500.00" not in on_disk
    assert RawMessage.objects.get(pk=raw.pk).body == "INR 500.00 debited from a/c XX1111"


def test_old_plain_rows_still_read_and_are_encrypted_when_saved_again():
    raw = RawMessage.objects.create(source="sms", sender="S", header="S", content_hash="h2", body="x",
                                    sent_at=dt.datetime.now(dt.timezone.utc))
    with connection.cursor() as cursor:
        cursor.execute("UPDATE ingest_rawmessage SET body = %s WHERE id = %s", ["plain old text", raw.pk])
    again = RawMessage.objects.get(pk=raw.pk)
    assert again.body == "plain old text"
    RawMessage.objects.filter(pk=raw.pk).update(body=again.body)
    assert stored_text(raw.pk).startswith("enc1:")
