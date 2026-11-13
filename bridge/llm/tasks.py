import logging

from celery import shared_task

from ingest.models import ReviewItem

from . import fallback, providers

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def suggest_for_review(self, item_id):
    """Attach a checked AI reading to an 'unparsed' review item. Never posts anything."""
    item = ReviewItem.objects.select_related("raw").get(pk=item_id)
    if item.status != ReviewItem.Status.OPEN or item.raw is None or item.suggestion:
        return "skipped"
    try:
        suggestion = fallback.suggest(item.raw)
        item.suggestion = {"status": "ok", **suggestion}
    except fallback.Rejected as exc:
        item.suggestion = {"status": "rejected", "reason": str(exc)}
    except providers.LLMError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300)  # e.g. the Mac was asleep; try again later
        item.suggestion = {"status": "error", "reason": str(exc)}
    item.save(update_fields=["suggestion"])
    log.info("review item %s: AI suggestion %s", item_id, item.suggestion["status"])
    return item.suggestion["status"]
