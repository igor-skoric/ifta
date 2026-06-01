"""Validation before creating or updating dispatch loads."""

from __future__ import annotations

from datetime import date

from .assignments import attach_current_equipment_to_drivers, get_driver_trailers, get_driver_truck
from .driver_availability import driver_unavailable_on_date
from .models import DispatchDriver, DispatchLoad


def collect_load_schedule_dates(
    load: DispatchLoad,
    *,
    anchor_date: date | None = None,
) -> list[date]:
    """Distinct calendar days to check for driver unavailability."""
    days: list[date] = []

    def add(day: date | None) -> None:
        if day and day not in days:
            days.append(day)

    add(anchor_date)
    if load.pickup_datetime:
        add(load.pickup_datetime.date())
    if load.delivery_datetime:
        add(load.delivery_datetime.date())
    elif load.planner_date:
        add(load.planner_date)
    return days


def _dispatcher_display(dispatcher) -> str:
    return f"{dispatcher.first_name} {dispatcher.last_name}".strip() or dispatcher.employee_id


def validate_driver_assignment_for_load(
    driver: DispatchDriver,
    *,
    check_dates: list[date] | None = None,
) -> list[str]:
    """
    Ensure driver, dispatcher, truck, and trailers are active and driver is available
    on scheduled day(s). Returns human-readable error messages (may be multiple).
    """
    attach_current_equipment_to_drivers([driver])
    errors: list[str] = []
    name = driver.display_name

    if not driver.is_active:
        errors.append(f"Driver {name} is inactive and cannot be assigned a new load.")

    dispatcher = driver.dispatcher
    if not dispatcher:
        errors.append(f"Driver {name} has no dispatcher assigned.")
    else:
        if not dispatcher.is_active:
            errors.append(
                f"Dispatcher {_dispatcher_display(dispatcher)} is inactive "
                f"(assigned to {name})."
            )
        elif not dispatcher.is_dispatcher:
            errors.append(
                f"{_dispatcher_display(dispatcher)} is not marked as a dispatcher "
                f"(assigned to {name})."
            )

    truck = get_driver_truck(driver)
    if not truck:
        errors.append(f"Driver {name} has no truck assigned.")
    elif not truck.is_active:
        errors.append(f"Truck {truck.unit_number} (assigned to {name}) is inactive.")

    for trailer in get_driver_trailers(driver):
        if not trailer.is_active:
            errors.append(
                f"Trailer {trailer.unit_number} (assigned to {name}) is inactive."
            )

    if check_dates:
        for day in check_dates:
            block = driver_unavailable_on_date(driver.pk, day)
            if block:
                note = f" ({block.note})" if block.note else ""
                errors.append(
                    f"{name} is unavailable on {day:%b %d, %Y} "
                    f"({block.get_reason_display()}){note}."
                )

    return errors


def validate_load_driver(
    load: DispatchLoad,
    *,
    anchor_date: date | None = None,
) -> list[str]:
    if not load.driver_id:
        return []
    driver = load.driver
    if driver is None:
        driver = DispatchDriver.objects.select_related("dispatcher").get(pk=load.driver_id)
    return validate_driver_assignment_for_load(
        driver,
        check_dates=collect_load_schedule_dates(load, anchor_date=anchor_date),
    )
