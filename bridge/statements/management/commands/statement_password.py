"""Store statement passwords, typed into a hidden prompt (never on the command line, never shown).

  docker compose run --rm bridge python manage.py statement_password set hsbc --label savings
  docker compose run --rm bridge python manage.py statement_password setup cdsl   (one bank only)
  docker compose run --rm bridge python manage.py statement_password list
  docker compose run --rm bridge python manage.py statement_password delete hsbc --label savings
"""
import getpass

from django.core.management.base import BaseCommand, CommandError

from statements import passwords
from statements.models import StatementPassword

KEYS = ["hsbc", "icici", "axis-card", "sbi-card", "hdfc", "cdsl"]
HINTS = {  # the rule each bank states in its statement email; the password itself is never written here
    "hsbc": "date of birth as DDMMYY + the digits of your Customer ID the email names",
    "icici": "first letters of the account name + DDMM of birth, lowercase",
    "axis-card": "first 4 letters of your name in CAPITALS + DDMM of birth (works for both Axis cards)",
    "sbi-card": "the format in your SBI Card statement email",
    "hdfc": "the format in your HDFC statement email (press Enter to skip if you get none)",
    "cdsl": "your PAN in CAPITALS (as the CDSL CAS email says)",
}


class Command(BaseCommand):
    help = "Store, list or delete encrypted statement passwords."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["setup", "set", "list", "delete"])
        parser.add_argument("key", nargs="?", choices=KEYS)
        parser.add_argument("--label", default="default", help="your note, e.g. the card name; not the password")

    def handle(self, *args, action, key, label, **options):
        if action == "list":
            for p in StatementPassword.objects.order_by("key", "label"):
                self.stdout.write(f"{p.key:10} {p.label:20} saved {p.created_at:%d %b %Y}")
            return
        if action == "setup":
            self._setup([key] if key else KEYS)
            return
        if not key:
            raise CommandError(f"which bank? one of {', '.join(KEYS)}")
        if action == "delete":
            deleted, _ = StatementPassword.objects.filter(key=key, label=label).delete()
            self.stdout.write("deleted" if deleted else "nothing to delete")
            return
        first = getpass.getpass(f"Password for {key} ({label}) - typing is hidden: ")
        second = getpass.getpass("Type it again: ")
        if not first or first != second:
            raise CommandError("the two entries did not match; nothing saved")
        passwords.save(key, label, first)
        self.stdout.write(self.style.SUCCESS(f"saved {key}/{label} (encrypted)"))

    def _setup(self, keys):
        """Ask once per bank and check the password against that bank's downloaded statements right away,
        instead of asking twice (some terminals mangle the second hidden entry)."""
        from mail.models import StatementAttachment
        from statements import pdf

        self.stdout.write("Type each bank's statement password. Typing is hidden. Press Enter to skip a bank.")
        self.stdout.write("Each password is tested on that bank's downloaded statements and saved only if it opens them.\n")
        for bank in keys:
            files = list(StatementAttachment.objects.filter(key=bank).exclude(local_file="")
                         .exclude(filename__icontains="important").values_list("local_file", flat=True))
            self.stdout.write(f"{bank}: {HINTS[bank]}  ({len(files)} statements downloaded)")
            for attempt in range(3):
                typed = getpass.getpass("  password: ").strip()
                if not typed:
                    self.stdout.write("  skipped\n")
                    break
                if not files:
                    passwords.save(bank, "default", typed)
                    self.stdout.write(self.style.SUCCESS("  saved (encrypted); no statement to test it on yet\n"))
                    break
                opened = 0
                for path in files:
                    try:
                        index, _ = pdf.unlock(path, [typed])
                        opened += index == 0
                    except pdf.PdfError:
                        pass
                if opened:
                    passwords.save(bank, "default", typed)
                    self.stdout.write(self.style.SUCCESS(f"  opens {opened} of {len(files)} statements - saved (encrypted)\n"))
                    break
                self.stdout.write(self.style.ERROR(
                    f"  that ({len(typed)} characters) did not open any {bank} statement; check the format and capital letters"))
            else:
                self.stdout.write("  skipped after 3 tries\n")
