"""Application timezone helpers (default: US Central / America/Chicago)."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def app_timezone():
    name = getattr(settings, "TIME_ZONE", "America/Chicago")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def app_now():
    """Current time in the application timezone (Django TIME_ZONE)."""
    return timezone.localtime(timezone.now())
