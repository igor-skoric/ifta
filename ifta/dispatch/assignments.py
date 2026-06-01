"""Driver ↔ truck ↔ trailer assignments with history (ended_at)."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import DispatchAssignment, DispatchDriver, DispatchTrailer, DispatchTruck


def current_assignments():
    return DispatchAssignment.objects.filter(ended_at__isnull=True)


def _now():
    return timezone.now()


def _end_assignments(qs) -> int:
    return qs.filter(ended_at__isnull=True).update(ended_at=_now())


def get_driver_truck(driver: DispatchDriver) -> DispatchTruck | None:
    if hasattr(driver, "_assignment_truck"):
        return driver._assignment_truck
    row = (
        current_assignments()
        .filter(driver=driver, truck__isnull=False)
        .select_related("truck")
        .order_by("-started_at", "-pk")
        .first()
    )
    return row.truck if row else None


def get_driver_trailers(driver: DispatchDriver) -> list[DispatchTrailer]:
    if hasattr(driver, "_assignment_trailers"):
        return driver._assignment_trailers
    return list(
        DispatchTrailer.objects.filter(
            assignments__driver=driver,
            assignments__ended_at__isnull=True,
            assignments__trailer__isnull=False,
        )
        .order_by("unit_number")
        .distinct()
    )


def get_truck_driver(truck: DispatchTruck) -> DispatchDriver | None:
    if hasattr(truck, "_assignment_driver"):
        return truck._assignment_driver
    row = (
        current_assignments()
        .filter(truck=truck)
        .select_related("driver")
        .order_by("-started_at", "-pk")
        .first()
    )
    return row.driver if row else None


def get_trailer_driver(trailer: DispatchTrailer) -> DispatchDriver | None:
    if hasattr(trailer, "_assignment_driver"):
        return trailer._assignment_driver
    row = (
        current_assignments()
        .filter(trailer=trailer)
        .select_related("driver")
        .order_by("-started_at", "-pk")
        .first()
    )
    return row.driver if row else None


def get_trailer_truck(trailer: DispatchTrailer) -> DispatchTruck | None:
    if hasattr(trailer, "_assignment_truck"):
        return trailer._assignment_truck
    row = (
        current_assignments()
        .filter(trailer=trailer, truck__isnull=False)
        .select_related("truck")
        .order_by("-started_at", "-pk")
        .first()
    )
    return row.truck if row else None


def get_truck_trailers(truck: DispatchTruck) -> list[DispatchTrailer]:
    if hasattr(truck, "_assignment_trailers"):
        return truck._assignment_trailers
    return list(
        DispatchTrailer.objects.filter(
            assignments__truck=truck,
            assignments__ended_at__isnull=True,
            assignments__trailer__isnull=False,
        )
        .order_by("unit_number")
        .distinct()
    )


class _CurrentTrailerRelated:
    """Template-compatible stand-in for the old driver.trailers related manager."""

    def __init__(self, driver: DispatchDriver):
        self.driver = driver

    def all(self):
        return get_driver_trailers(self.driver)


def attach_current_equipment_to_drivers(drivers: Iterable[DispatchDriver]) -> None:
    drivers = list(drivers)
    if not drivers:
        return
    ids = [d.pk for d in drivers]
    rows = (
        current_assignments()
        .filter(driver_id__in=ids)
        .select_related("truck", "trailer")
        .order_by("driver_id", "-started_at", "-pk")
    )
    by_driver: dict[int, list] = defaultdict(list)
    for row in rows:
        by_driver[row.driver_id].append(row)
    for driver in drivers:
        assigns = by_driver.get(driver.pk, [])
        truck = next((a.truck for a in assigns if a.truck_id), None)
        seen_trailer_ids: set[int] = set()
        trailers: list[DispatchTrailer] = []
        for a in assigns:
            if a.trailer_id and a.trailer_id not in seen_trailer_ids:
                seen_trailer_ids.add(a.trailer_id)
                trailers.append(a.trailer)
        trailers.sort(key=lambda t: t.unit_number)
        driver._assignment_truck = truck
        driver._assignment_trailers = trailers


def attach_current_driver_to_trucks(trucks: Iterable[DispatchTruck]) -> None:
    trucks = list(trucks)
    if not trucks:
        return
    ids = [t.pk for t in trucks]
    rows = (
        current_assignments()
        .filter(truck_id__in=ids)
        .select_related("driver", "driver__dispatcher", "trailer")
        .order_by("truck_id", "-started_at", "-pk")
    )
    by_truck: dict[int, dict] = {}
    for row in rows:
        entry = by_truck.setdefault(
            row.truck_id,
            {"driver": None, "trailers": [], "seen_trailer_ids": set()},
        )
        if entry["driver"] is None and row.driver_id:
            entry["driver"] = row.driver
        if row.trailer_id and row.trailer_id not in entry["seen_trailer_ids"]:
            entry["seen_trailer_ids"].add(row.trailer_id)
            entry["trailers"].append(row.trailer)
    for truck in trucks:
        entry = by_truck.get(truck.pk, {"driver": None, "trailers": []})
        truck._assignment_driver = entry["driver"]
        truck._assignment_trailers = sorted(
            entry["trailers"], key=lambda tr: tr.unit_number
        )


def attach_current_driver_to_trailers(trailers: Iterable[DispatchTrailer]) -> None:
    trailers = list(trailers)
    if not trailers:
        return
    ids = [t.pk for t in trailers]
    rows = (
        current_assignments()
        .filter(trailer_id__in=ids)
        .select_related("driver", "driver__dispatcher", "truck")
        .order_by("trailer_id", "-started_at", "-pk")
    )
    by_trailer: dict[int, dict] = {}
    for row in rows:
        if row.trailer_id not in by_trailer:
            by_trailer[row.trailer_id] = {
                "driver": row.driver if row.driver_id else None,
                "truck": row.truck if row.truck_id else None,
            }
    for trailer in trailers:
        entry = by_trailer.get(trailer.pk, {"driver": None, "truck": None})
        trailer._assignment_driver = entry["driver"]
        trailer._assignment_truck = entry["truck"]


def assigned_truck_ids() -> list[int]:
    return list(
        current_assignments()
        .filter(truck__isnull=False)
        .values_list("truck_id", flat=True)
        .distinct()
    )


def assigned_trailer_ids() -> list[int]:
    return list(
        current_assignments()
        .filter(trailer__isnull=False)
        .values_list("trailer_id", flat=True)
        .distinct()
    )


def clear_equipment(
    *,
    driver: DispatchDriver | None = None,
    truck: DispatchTruck | None = None,
    trailer: DispatchTrailer | None = None,
) -> None:
    """End current assignment rows touching any of the given entities."""
    if driver:
        _end_assignments(current_assignments().filter(driver=driver))
    if truck:
        _end_assignments(current_assignments().filter(truck=truck))
    if trailer:
        _end_assignments(current_assignments().filter(trailer=trailer))


@transaction.atomic
def set_assignment(
    *,
    driver: DispatchDriver | None = None,
    truck: DispatchTruck | None = None,
    trailer: DispatchTrailer | None = None,
) -> None:
    """Create one current assignment row; ends prior rows for each non-null entity."""
    if not any([driver, truck, trailer]):
        return
    now = _now()
    clear_equipment(driver=driver, truck=truck, trailer=trailer)
    DispatchAssignment.objects.create(
        driver=driver,
        truck=truck,
        trailer=trailer,
        started_at=now,
    )


@transaction.atomic
def set_driver_equipment(
    driver: DispatchDriver,
    *,
    truck: DispatchTruck | None = None,
    trailer: DispatchTrailer | None = None,
) -> None:
    """Replace driver's current equipment with at most one truck and one trailer."""
    clear_equipment(driver=driver)
    if truck or trailer:
        set_assignment(driver=driver, truck=truck, trailer=trailer)


@transaction.atomic
def set_truck_equipment(
    truck: DispatchTruck,
    *,
    driver: DispatchDriver | None = None,
    trailer: DispatchTrailer | None = None,
) -> None:
    """Set truck with optional driver and/or trailer (no driver required)."""
    set_assignment(driver=driver, truck=truck, trailer=trailer)


@transaction.atomic
def set_trailer_equipment(
    trailer: DispatchTrailer,
    *,
    driver: DispatchDriver | None = None,
    truck: DispatchTruck | None = None,
) -> None:
    """Set trailer with optional truck and/or driver."""
    set_assignment(driver=driver, truck=truck, trailer=trailer)


@transaction.atomic
def assign_driver_truck(
    driver: DispatchDriver | None,
    truck: DispatchTruck,
    *,
    carry_trailers: bool = True,
) -> None:
    """Assign or unassign driver on a truck; keeps trailer pairing when driver cleared."""
    trailer = None
    if carry_trailers:
        on_truck = get_truck_trailers(truck)
        trailer = on_truck[0] if on_truck else None
    if driver:
        if carry_trailers and not trailer:
            driver_trailers = get_driver_trailers(driver)
            trailer = driver_trailers[0] if driver_trailers else None
        set_assignment(driver=driver, truck=truck, trailer=trailer)
    else:
        set_assignment(driver=None, truck=truck, trailer=trailer)


@transaction.atomic
def assign_driver_trailer(
    driver: DispatchDriver | None,
    trailer: DispatchTrailer,
) -> None:
    """Assign or unassign driver on a trailer; keeps truck link when driver cleared."""
    truck = get_trailer_truck(trailer)
    if driver:
        if not truck:
            truck = get_driver_truck(driver)
        set_assignment(driver=driver, truck=truck, trailer=trailer)
    else:
        set_assignment(driver=None, truck=truck, trailer=trailer)


def drivers_without_current_truck(exclude_driver_id: int | None = None):
    """Active drivers that do not currently have a truck assignment."""
    assigned_driver_ids = set(
        current_assignments()
        .filter(truck__isnull=False)
        .values_list("driver_id", flat=True)
        .distinct()
    )
    qs = DispatchDriver.objects.filter(is_active=True).order_by(
        "sort_order", "last_name", "first_name"
    )
    if exclude_driver_id:
        return qs.filter(Q(pk=exclude_driver_id) | ~Q(pk__in=assigned_driver_ids))
    return qs.filter(~Q(pk__in=assigned_driver_ids))


def active_assignment_filter(prefix: str = "") -> Q:
    """Q for joining assignments that are still current."""
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}ended_at__isnull": True})


def current_assignment_q(prefix: str = "assignments") -> Q:
    """Filter related equipment via active assignment rows (for search / filters)."""
    return Q(**{f"{prefix}__ended_at__isnull": True})


def truck_search_q(q: str) -> Q:
    active = current_assignment_q("assignments")
    return (
        Q(unit_number__icontains=q)
        | Q(notes__icontains=q)
        | Q(active, assignments__driver__first_name__icontains=q)
        | Q(active, assignments__driver__last_name__icontains=q)
        | Q(active, assignments__driver__legacy_driver_id__icontains=q)
        | Q(active, assignments__driver__phone__icontains=q)
        | Q(active, assignments__driver__email__icontains=q)
        | Q(active, assignments__driver__notes__icontains=q)
        | Q(active, assignments__driver__dispatcher__first_name__icontains=q)
        | Q(active, assignments__driver__dispatcher__last_name__icontains=q)
        | Q(active, assignments__driver__dispatcher__employee_id__icontains=q)
        | Q(active, assignments__driver__dispatcher__work_email__icontains=q)
    )


def trailer_search_q(q: str) -> Q:
    active = current_assignment_q("assignments")
    return (
        Q(unit_number__icontains=q)
        | Q(notes__icontains=q)
        | Q(active, assignments__driver__first_name__icontains=q)
        | Q(active, assignments__driver__last_name__icontains=q)
        | Q(active, assignments__driver__legacy_driver_id__icontains=q)
        | Q(active, assignments__driver__phone__icontains=q)
        | Q(active, assignments__driver__email__icontains=q)
        | Q(active, assignments__driver__notes__icontains=q)
        | Q(active, assignments__driver__dispatcher__first_name__icontains=q)
        | Q(active, assignments__driver__dispatcher__last_name__icontains=q)
        | Q(active, assignments__driver__dispatcher__employee_id__icontains=q)
        | Q(active, assignments__driver__dispatcher__work_email__icontains=q)
    )


def load_search_q(q: str) -> Q:
    filters = (
        Q(broker_or_customer__icontains=q)
        | Q(pickup_city__icontains=q)
        | Q(pickup_state__icontains=q)
        | Q(delivery_city__icontains=q)
        | Q(delivery_state__icontains=q)
        | Q(bol_number__icontains=q)
        | Q(po_number__icontains=q)
        | Q(notes__icontains=q)
        | Q(equipment_type__icontains=q)
        | Q(driver__first_name__icontains=q)
        | Q(driver__last_name__icontains=q)
        | Q(driver__legacy_driver_id__icontains=q)
        | Q(driver__phone__icontains=q)
        | Q(driver__email__icontains=q)
    )
    if q.isdigit():
        filters |= Q(pk=int(q))
    return filters


def driver_search_q(q: str) -> Q:
    from django.utils.dateparse import parse_date

    from .models import DispatchDriver

    ql = q.lower()
    active = current_assignment_q("assignments")
    filters = (
        Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(legacy_driver_id__icontains=q)
        | Q(driveroo_status__icontains=q)
        | Q(fleet_company__icontains=q)
        | Q(comp_oo_local_legal__icontains=q)
        | Q(dispatcher__first_name__icontains=q)
        | Q(dispatcher__last_name__icontains=q)
        | Q(dispatcher__employee_id__icontains=q)
        | Q(dispatcher__work_email__icontains=q)
        | Q(active, assignments__truck__unit_number__icontains=q)
        | Q(active, assignments__truck__notes__icontains=q)
        | Q(active, assignments__trailer__unit_number__icontains=q)
        | Q(active, assignments__trailer__notes__icontains=q)
        | Q(phone__icontains=q)
        | Q(email__icontains=q)
        | Q(notes__icontains=q)
    )
    for key, label in DispatchDriver.FleetCompany.choices:
        if ql in label.lower() or ql in key.lower():
            filters |= Q(fleet_company=key)
    for key, label in DispatchDriver.CompOoLocalLegal.choices:
        if ql in label.lower() or ql in key.lower():
            filters |= Q(comp_oo_local_legal=key)
    parsed_hire = parse_date(q)
    if parsed_hire:
        filters |= Q(hire_date=parsed_hire)
    return filters


def assignment_history_for_driver(driver: DispatchDriver, *, limit: int = 50):
    return (
        DispatchAssignment.objects.filter(driver=driver)
        .select_related("truck", "trailer", "driver")
        .order_by("-started_at", "-pk")[:limit]
    )


def assignment_history_for_truck(truck: DispatchTruck, *, limit: int = 50):
    return (
        DispatchAssignment.objects.filter(truck=truck)
        .select_related("driver", "trailer", "driver__dispatcher")
        .order_by("-started_at", "-pk")[:limit]
    )


def assignment_history_for_trailer(trailer: DispatchTrailer, *, limit: int = 50):
    return (
        DispatchAssignment.objects.filter(trailer=trailer)
        .select_related("driver", "truck", "driver__dispatcher")
        .order_by("-started_at", "-pk")[:limit]
    )


def current_assignments_for_driver(driver: DispatchDriver):
    return (
        current_assignments()
        .filter(driver=driver)
        .select_related("truck", "trailer")
        .order_by("-started_at", "-pk")
    )
