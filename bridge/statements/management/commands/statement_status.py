"""Statement PDFs and what state they are in. With --peek ID, prints that statement's text with every digit
replaced by '#', for writing parsers. Nothing unlocked is written to disk."""
from django.core.management.base import BaseCommand

from mail.models import StatementAttachment
from statements.tasks import read_pages


class Command(BaseCommand):
    help = "List statement PDFs, or --peek ID to see one statement's layout with digits masked."

    def add_arguments(self, parser):
        parser.add_argument("--peek", type=int)
        parser.add_argument("--pages", type=int, default=2)

    def handle(self, *args, peek, pages, **options):
        import re

        if peek is None:
            for a in StatementAttachment.objects.order_by("key", "sent_at"):
                when = f"{a.sent_at:%Y-%m-%d}" if a.sent_at else "?"
                self.stdout.write(f"{a.pk:>4} {a.key:9} {when} {a.status:15} {re.sub(r'[0-9]', '#', a.subject)[:70]}")
            return
        texts = read_pages(StatementAttachment.objects.get(pk=peek))
        for n, page in enumerate(texts[:pages], 1):
            self.stdout.write(f"----- page {n} of {len(texts)}")
            self.stdout.write(re.sub(r"[0-9]", "#", page))
