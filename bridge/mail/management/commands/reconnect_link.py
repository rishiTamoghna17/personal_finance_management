"""Make a one-time reconnect link now (normally Celery does this from day 3). Prints the link; open it on a device
that is on your Tailscale.
  docker compose exec bridge python manage.py reconnect_link gmail:acct1     (or gmail:acct2, drive)
"""
import datetime as dt
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.crypto import encrypt
from mail import reconnect
from mail.models import ReconnectLink


class Command(BaseCommand):
    help = "Create a one-time Google reconnect link and print it."

    def add_arguments(self, parser):
        parser.add_argument("connection", help="gmail:<tag> or drive")

    def handle(self, *args, connection, **options):
        if not reconnect.enabled():
            raise CommandError("PUBLIC_BASE_URL must be the https:// Tailscale address")
        available = dict(reconnect.connections())
        combined_tag = reconnect.combined_gmail_tag()
        if combined_tag and connection == f"gmail:{combined_tag}":
            connection = f"gmail:{combined_tag}+drive"
        if connection not in available:
            raise CommandError(f"unknown connection; one of {', '.join(dict(reconnect.connections()))}")
        if not reconnect.client_for(connection)[1]:
            raise CommandError("no web sign-in client configured for this connection")
        link = reconnect.live_link(connection)
        if link is None:
            token = secrets.token_urlsafe(32)
            link = ReconnectLink.objects.create(
                connection=connection, token_hash=reconnect._hash(token), token_encrypted=encrypt(token),
                expires_at=timezone.now() + dt.timedelta(hours=settings.RECONNECT_LINK_HOURS))
        self.stdout.write(f"Open on a Tailscale device (valid until {timezone.localtime(link.expires_at):%d %b %H:%M}, once):")
        self.stdout.write(reconnect.link_url(link))
