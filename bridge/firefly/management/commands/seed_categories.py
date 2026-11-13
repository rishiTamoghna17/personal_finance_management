"""Create or update Firefly categories (with notes the AI categoriser reads) from categories.yaml. Safe to re-run.

  docker compose run --rm -T bridge python manage.py seed_categories - < categories.yaml
"""
import sys

import yaml
from django.core.management.base import BaseCommand, CommandError

from firefly.client import FireflyClient, FireflyError


class Command(BaseCommand):
    help = "Create or update Firefly categories from categories.yaml."

    def add_arguments(self, parser):
        parser.add_argument("path", help="categories.yaml, or - for stdin")

    def handle(self, *args, path, **options):
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        wanted = (yaml.safe_load(text) or {}).get("categories") or []
        if not all(isinstance(c, dict) and isinstance(c.get("name"), str) and c["name"].strip() for c in wanted):
            raise CommandError("each category needs a name")
        client = self.get_client()
        try:
            existing = {c["attributes"]["name"].strip().lower(): c for c in client.list_all("categories")}
            for item in wanted:
                name, notes = item["name"].strip(), (item.get("notes") or "").strip()
                found = existing.get(name.lower())
                if found is None:
                    client.create_category(name, notes)
                    self.stdout.write(self.style.SUCCESS(f"created  {name}"))
                elif (found["attributes"].get("notes") or "").strip() != notes:
                    client.update_category(found["id"], name, notes)
                    self.stdout.write(f"updated  {name}")
                else:
                    self.stdout.write(f"exists   {name}")
        except FireflyError as exc:
            raise CommandError(str(exc)) from None

    def get_client(self):
        return FireflyClient.from_settings()
