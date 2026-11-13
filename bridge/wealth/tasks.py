"""M5 beat tasks. No arguments carry money, text or secrets."""
import logging

from celery import shared_task
from django.utils import timezone

from . import dues, goals, networth

log = logging.getLogger(__name__)


@shared_task
def monthly_snapshot():
    snap = networth.snapshot(networth.last_month_end())
    log.info("net worth snapshot stored for %s", snap.taken_on)
    return str(snap.taken_on)


@shared_task
def check_dues():
    counts = dues.check_dues(timezone.localdate())
    updated = goals.refresh_progress()
    log.info("card dues checked %s; %s goals refreshed", counts, updated)
    return counts
