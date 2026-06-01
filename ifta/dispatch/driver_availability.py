"""Driver time-off / unavailability for the load planner."""

from __future__ import annotations

from datetime import date

from .models import DriverUnavailability


def entry_covers_date(entry: DriverUnavailability, day: date) -> bool:
    return entry.start_date <= day <= entry.end_date


def entries_for_drivers_between(
    driver_ids: list[int],
    *,
    start: date,
    end: date,
) -> list[DriverUnavailability]:
    if not driver_ids:
        return []
    return list(
        DriverUnavailability.objects.filter(
            driver_id__in=driver_ids,
            start_date__lte=end,
            end_date__gte=start,
        )
        .select_related("driver")
        .order_by("driver_id", "-start_date", "-pk")
    )


def unavailability_by_cell(
    entries: list[DriverUnavailability],
    *,
    driver_ids: list[int],
    days: list[date],
) -> dict[str, DriverUnavailability]:
    """Map ``{driver_id}_{iso-date}`` → entry (first match per cell)."""
    by_driver_day: dict[tuple[int, date], DriverUnavailability] = {}
    for entry in entries:
        if entry.driver_id not in driver_ids:
            continue
        for day in days:
            if not entry_covers_date(entry, day):
                continue
            key = (entry.driver_id, day)
            if key not in by_driver_day:
                by_driver_day[key] = entry
    return {f"{driver_id}_{day.isoformat()}": entry for (driver_id, day), entry in by_driver_day.items()}


def driver_unavailable_on_date(driver_id: int, day: date) -> DriverUnavailability | None:
    return (
        DriverUnavailability.objects.filter(
            driver_id=driver_id,
            start_date__lte=day,
            end_date__gte=day,
        )
        .order_by("-start_date", "-pk")
        .first()
    )
