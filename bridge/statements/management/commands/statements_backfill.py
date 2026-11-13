"""Fetch recent statement PDFs from Gmail (read-only) so parsers can be written and old balances confirmed.

  docker compose run --rm bridge python manage.py statements_backfill --months 6
"""
import datetime as dt

from django.core.management.base import BaseCommand

from ingest import parser
from mail import gmail
from mail.models import GmailAccount, StatementAttachment
from mail.tasks import statement_key
from mail.text import message_parts


class Command(BaseCommand):
    help = "Record and download statement PDFs from the last N months."

    def add_arguments(self, parser_):
        parser_.add_argument("--months", type=int, default=6)

    def handle(self, *args, months, **options):
        domains = sorted({h.lower() for h in parser.profiles("email")})
        query = f"newer_than:{months}m has:attachment filename:pdf from:({' OR '.join(domains)})"
        for account in GmailAccount.objects.filter(enabled=True):
            service = gmail.service_for(account)
            added = 0
            for message_id in gmail.list_ids(service, query):
                message = gmail.get_message(service, message_id)
                sender, subject, text, pdfs = message_parts(message)
                header = parser.header_of_email(sender)
                result = parser.parse(header, f"{subject}\n{text}", dt.datetime.now(parser.IST), "email")
                if not result.pattern_ref.endswith("/statement") or not pdfs:
                    continue  # only emails an email profile recognises as a statement
                sent_at = dt.datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=dt.timezone.utc)
                for item in pdfs:
                    _, created = StatementAttachment.objects.get_or_create(
                        gmail_message_id=message_id, filename=item["filename"],
                        defaults={"account": account, "attachment_id": item["attachment_id"], "size": item["size"],
                                  "key": statement_key(header), "subject": subject[:300], "sent_at": sent_at},
                    )
                    added += created
            self.stdout.write(f"{account.tag}: {added} new statement PDFs recorded")
        from statements.tasks import download

        for att in StatementAttachment.objects.filter(local_file="").select_related("account"):
            download(att)
        self.stdout.write("downloaded (still locked) to the statements folder")
