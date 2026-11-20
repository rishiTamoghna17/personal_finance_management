from celery import shared_task


@shared_task
def dispatch_push_notifications():
    from .push import dispatch_alerts

    return dispatch_alerts()


@shared_task
def dispatch_weekly_push_digest():
    from .push import dispatch_weekly_digest

    return dispatch_weekly_digest()
