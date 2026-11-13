"""Create the Firefly webhook that sends each new transaction to the AI categoriser. Safe to re-run.

  docker compose run --rm bridge python manage.py setup_categorizer
"""
from django.core.management.base import BaseCommand, CommandError

from firefly.client import FireflyClient, FireflyError

TITLE = "AI categoriser (internal)"
URL = "http://categorizer:3000/webhook"  # Docker network only; never published to the Wi-Fi or the internet


class Command(BaseCommand):
    help = "Create the Firefly webhook for the AI categoriser."

    def handle(self, *args, **options):
        client = FireflyClient.from_settings()
        try:
            for hook in client.list_all("webhooks"):
                if hook["attributes"].get("title") == TITLE:
                    self.stdout.write(f"exists   {TITLE} -> {hook['attributes'].get('url')}")
                    return
            client.create_webhook({"title": TITLE, "url": URL, "active": True, "triggers": ["STORE_TRANSACTION"],
                                   "responses": ["TRANSACTIONS"], "deliveries": ["JSON"]})
        except FireflyError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS(f"created  {TITLE} -> {URL}"))
