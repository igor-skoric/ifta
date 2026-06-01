"""ISO week scope for weekly analytics (sync + API).

Default timezone is America/Chicago. Override in Django settings:

    STATISTIC_WEEK_TIMEZONE = "Europe/Belgrade"
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def week_timezone():
    name = getattr(settings, "STATISTIC_WEEK_TIMEZONE", None) or getattr(
        settings, "TIME_ZONE", "America/Chicago"
    )
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def current_iso_year_week():
    """Return (iso_year, iso_week) for *today* in the configured week timezone."""
    tz = week_timezone()
    d = timezone.now().astimezone(tz).date()
    ic = d.isocalendar()
    return ic.year, ic.week
