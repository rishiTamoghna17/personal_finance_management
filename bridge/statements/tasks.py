"""Statement PDFs: download (as sent, still locked), unlock in memory, parse. Task arguments are row ids only."""
import logging
import os

from celery import shared_task
from django.conf import settings

from mail import gmail
from mail.models import StatementAttachment

from . import passwords, pdf
from .parsers import registry

log = logging.getLogger(__name__)
S = StatementAttachment.Status


def download(att):
    folder = settings.STATEMENT_DIR / (att.key or "unknown")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / f"{att.gmail_message_id}_{os.path.basename(att.filename)}"
    if not path.exists():
        data = gmail.get_attachment(gmail.service_for(att.account), att.gmail_message_id, att.attachment_id)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    att.local_file, att.status = str(path), S.DOWNLOADED
    att.save(update_fields=["local_file", "status"])


def read_pages(att):
    """Unlocked page texts, in memory. Raises pdf.PdfError."""
    _, pages = pdf.unlock(att.local_file, passwords.candidates(att.key))
    return pages


@shared_task
def process_attachment(att_id):
    att = StatementAttachment.objects.select_related("account").get(pk=att_id)
    if att.status in (S.DONE, S.SKIPPED):
        return att.status
    if "important" in att.filename.lower() or "faq" in att.filename.lower():
        att.status, att.detail = S.SKIPPED, "information leaflet, not a statement"
        att.save(update_fields=["status", "detail"])
        return att.status
    try:
        if not att.local_file:
            download(att)
        pages = read_pages(att)
    except pdf.PdfError as exc:
        att.status, att.detail = S.NEEDS_PASSWORD, str(exc)[:300]
        att.save(update_fields=["status", "detail"])
        return att.status
    except gmail.GmailError as exc:
        att.status, att.detail = S.FAILED, str(exc)[:300]
        att.save(update_fields=["status", "detail"])
        return att.status
    parser_fn = registry.find(att.key, pages)
    if parser_fn is None:
        att.status, att.detail = S.NEEDS_PARSER, "no parser for this statement layout yet"
        att.save(update_fields=["status", "detail"])
        return att.status
    from .reconcile import apply_statement

    result = apply_statement(att, parser_fn(pages))
    att.status, att.detail = S.DONE, result[:300]
    att.save(update_fields=["status", "detail"])
    log.info("statement %s processed: %s", att_id, result)
    return att.status


@shared_task
def process_pending():
    # needs_parser waits for a new parser to be deployed (then run statement_status --retry), not every hour.
    waiting = StatementAttachment.objects.filter(status__in=[S.PENDING, S.DOWNLOADED, S.NEEDS_PASSWORD])
    for att_id in waiting.values_list("pk", flat=True):
        process_attachment.delay(att_id)
