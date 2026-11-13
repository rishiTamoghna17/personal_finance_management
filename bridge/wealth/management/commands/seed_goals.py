"""Create or update goals (Firefly piggy banks) from goals.yaml. Safe to re-run.

  docker compose run --rm -T bridge python manage.py seed_goals - < goals.yaml
  docker compose run --rm -T bridge python manage.py seed_goals --dry-run - < goals.yaml
"""
import sys

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.money import format_inr
from firefly.client import FireflyClient, FireflyError
from wealth import goals


class Command(BaseCommand):
    help = "Create or update goals in Firefly from goals.yaml (read from a file or stdin '-')."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, path, dry_run, **options):
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        client = FireflyClient.from_settings()
        try:
            planned = goals.plan(yaml.safe_load(text), client, timezone.localdate())
            for g in planned:
                self.stdout.write(f"{g['name']}: target {format_inr(g['target_paise'])}"
                                  f"{' by ' + g['target_date'].isoformat() if g['target_date'] else ''}")
            if dry_run:
                self.stdout.write("dry run: nothing sent to Firefly")
                return
            for name, result in goals.sync(planned, client):
                self.stdout.write(self.style.SUCCESS(f"{result}: {name}"))
        except (goals.GoalError, FireflyError) as exc:
            raise CommandError(str(exc)) from None
