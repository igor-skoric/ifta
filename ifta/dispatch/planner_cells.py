"""Planner grid cell content: delivery city on delivery day, arrow on pickup-only day."""

from __future__ import annotations

from datetime import date

from .models import DispatchLoad


def _append_unique(target: list[str], label: str) -> None:
    label = (label or "").strip()
    if label and label not in target:
        target.append(label)


def _collect_deliveries(loads: list[DispatchLoad], cell_date: date) -> list[str]:
    deliveries: list[str] = []
    for ld in loads:
        if ld.delivery_planner_date() == cell_date:
            _append_unique(deliveries, ld.delivery_display())
    return deliveries


def _has_pickup_only_on_date(loads: list[DispatchLoad], cell_date: date) -> bool:
    """Pick up this day, delivery on another day (or not set on this day)."""
    for ld in loads:
        pickup_day = ld.pickup_planner_date()
        if pickup_day != cell_date:
            continue
        delivery_day = ld.delivery_planner_date()
        if delivery_day != cell_date:
            return True
    return False


def _cell_from_deliveries(deliveries: list[str]) -> dict:
    if len(deliveries) > 1:
        return {
            "mode": "multi_delivery",
            "deliveries": deliveries,
            "text": deliveries[-1],
        }
    if deliveries:
        return {
            "mode": "delivery",
            "text": deliveries[-1],
            "deliveries": deliveries,
        }
    return {"mode": "empty", "text": ""}


def events_for_loads_on_date(loads: list[DispatchLoad], cell_date: date) -> dict:
    """Delivery city when delivering this day; arrow when pick up only."""
    if not loads:
        return {"mode": "empty", "text": ""}

    deliveries = _collect_deliveries(loads, cell_date)
    if deliveries:
        return _cell_from_deliveries(deliveries)

    if _has_pickup_only_on_date(loads, cell_date):
        return {"mode": "pickup", "text": "→"}

    return {"mode": "empty", "text": ""}


def primary_load_for_cell(loads: list[DispatchLoad], cell_date: date) -> DispatchLoad | None:
    """Load used for status color / dialog when several overlap one day."""
    if not loads:
        return None
    for load in loads:
        if load.delivery_planner_date() == cell_date:
            return load
    for load in loads:
        if load.pickup_planner_date() == cell_date:
            return load
    return loads[0]


def planner_days_for_load(load: DispatchLoad, *, monday: date, sunday: date) -> set[date]:
    """Calendar days this load should appear on the grid (pickup + delivery)."""
    days: set[date] = set()
    for day in (load.delivery_planner_date(), load.pickup_planner_date()):
        if day and monday <= day <= sunday:
            days.add(day)
    return days
