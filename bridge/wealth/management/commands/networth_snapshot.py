"""Store a net worth snapshot (normally done by beat on the 1st for the month just ended).

  docker compose run --rm bridge python manage.py networth_snapshot            # end of last month
  docker compose run --rm bridge python manage.py networth_snapshot --date 2026-11-14
"""
import datetime as dt

from django.core.management.base import BaseCommand

from core.money import format_inr
from wealth import networth


class Command(BaseCommand):
    help = "Store the net worth at the end of a date (default: last month end)."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=dt.date.fromisoformat)

    def handle(self, *args, date, **options):
        snap = networth.snapshot(date or networth.last_month_end())
        self.stdout.write(f"{snap.taken_on}: assets {format_inr(snap.assets_paise)}, liabilities "
                          f"{format_inr(snap.liabilities_paise)}, net worth {format_inr(snap.net_worth_paise)}")
