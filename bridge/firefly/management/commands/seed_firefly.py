import sys

import yaml
from django.core.management.base import BaseCommand, CommandError

from firefly.client import FireflyClient, FireflyError
from firefly.seed import CURRENCY, SeedError, build_plan


class Command(BaseCommand):
    help = "Set INR as Firefly's primary currency and create accounts from accounts.yaml. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to accounts.yaml, or - to read it from stdin")
        parser.add_argument("--dry-run", action="store_true", help="Validate the file and stop")

    def handle(self, *args, **options):
        try:
            text = sys.stdin.read() if options["path"] == "-" else open(options["path"], encoding="utf-8").read()
            payloads, planned = build_plan(yaml.safe_load(text))
        except (OSError, yaml.YAMLError) as exc:
            raise CommandError(f"cannot read accounts file: {type(exc).__name__}") from None
        except SeedError as exc:
            raise CommandError(str(exc)) from None

        for name in planned:
            self.stdout.write(f"planned  {name} (not created in Firefly until status is active)")
        if options["dry_run"]:
            for payload in payloads:
                self.stdout.write(f"valid    {payload['name']}")
            return

        client = self.get_client()
        if not client.has_token:
            raise CommandError("FIREFLY_ACCESS_TOKEN is not set in .env")
        try:
            client.enable_currency(CURRENCY)
            client.make_primary_currency(CURRENCY)
            self.stdout.write(f"currency {CURRENCY} enabled and set as primary")
            existing = {
                item["attributes"]["name"].strip().lower()
                for kind in ("asset", "liabilities")
                for item in client.list_accounts(kind)
            }
            for payload in payloads:
                if payload["name"].lower() in existing:
                    self.stdout.write(f"exists   {payload['name']}")
                    continue
                client.create_account(payload)
                self.stdout.write(self.style.SUCCESS(f"created  {payload['name']}"))
        except FireflyError as exc:
            raise CommandError(str(exc)) from None

    def get_client(self):
        return FireflyClient.from_settings()
