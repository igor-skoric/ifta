from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from .services.sync_sheet import sync_weekly_sheet, sync_dispatcher_sheet
import logging

logger = logging.getLogger(__name__)

scheduler = None


def start():
    global scheduler

    if not settings.DEBUG:
        return

    if scheduler:
        return

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        sync_dispatcher_sheet,
        "interval",
        minutes=1,
        id="sync_dispatcher_sheet",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    scheduler.add_job(
        sync_weekly_sheet,
        "interval",
        minutes=1,
        id="sync_weekly_sheet",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    scheduler.start()
