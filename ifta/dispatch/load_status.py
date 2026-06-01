"""Load status display tokens for planner cells and badges."""

from __future__ import annotations

from django.db import models

# Tailwind-aligned RGB for dark UI; each status has a distinct hue.
LOAD_STATUS_STYLES: dict[str, dict[str, str]] = {
    "load_booked": {
        "bg": "rgba(99, 102, 241, 0.42)",
        "border": "rgba(129, 140, 248, 0.65)",
        "text": "rgb(224, 231, 255)",
        "dot": "rgb(129, 140, 248)",
    },
    "heading_to_pickup": {
        "bg": "rgba(14, 165, 233, 0.4)",
        "border": "rgba(56, 189, 248, 0.65)",
        "text": "rgb(224, 242, 254)",
        "dot": "rgb(56, 189, 248)",
    },
    "at_pickup": {
        "bg": "rgba(6, 182, 212, 0.42)",
        "border": "rgba(34, 211, 238, 0.65)",
        "text": "rgb(207, 250, 254)",
        "dot": "rgb(34, 211, 238)",
    },
    "loaded": {
        "bg": "rgba(20, 184, 166, 0.42)",
        "border": "rgba(45, 212, 191, 0.65)",
        "text": "rgb(204, 251, 241)",
        "dot": "rgb(45, 212, 191)",
    },
    "in_transit": {
        "bg": "rgba(59, 130, 246, 0.42)",
        "border": "rgba(96, 165, 250, 0.65)",
        "text": "rgb(219, 234, 254)",
        "dot": "rgb(96, 165, 250)",
    },
    "at_delivery": {
        "bg": "rgba(245, 158, 11, 0.48)",
        "border": "rgba(251, 191, 36, 0.75)",
        "text": "rgb(255, 251, 235)",
        "dot": "rgb(251, 191, 36)",
    },
    "delivered": {
        "bg": "rgba(16, 185, 129, 0.45)",
        "border": "rgba(52, 211, 153, 0.7)",
        "text": "rgb(209, 250, 229)",
        "dot": "rgb(52, 211, 153)",
    },
    "empty": {
        "bg": "rgba(167, 139, 250, 0.38)",
        "border": "rgba(196, 181, 253, 0.6)",
        "text": "rgb(237, 233, 254)",
        "dot": "rgb(196, 181, 253)",
    },
    "layover": {
        "bg": "rgba(234, 179, 8, 0.4)",
        "border": "rgba(250, 204, 21, 0.7)",
        "text": "rgb(254, 249, 195)",
        "dot": "rgb(250, 204, 21)",
    },
    "breakdown": {
        "bg": "rgba(239, 68, 68, 0.42)",
        "border": "rgba(248, 113, 113, 0.7)",
        "text": "rgb(254, 226, 226)",
        "dot": "rgb(248, 113, 113)",
    },
    "cancelled": {
        "bg": "rgba(100, 116, 139, 0.45)",
        "border": "rgba(148, 163, 184, 0.55)",
        "text": "rgb(226, 232, 240)",
        "dot": "rgb(148, 163, 184)",
    },
}


class LoadStatus(models.TextChoices):
    LOAD_BOOKED = "load_booked", "Load Booked"
    HEADING_TO_PICKUP = "heading_to_pickup", "Heading to Pickup"
    AT_PICKUP = "at_pickup", "At Pickup"
    LOADED = "loaded", "Loaded"
    IN_TRANSIT = "in_transit", "In Transit"
    AT_DELIVERY = "at_delivery", "At Delivery"
    DELIVERED = "delivered", "Delivered"
    EMPTY = "empty", "Empty"
    LAYOVER = "layover", "Layover"
    BREAKDOWN = "breakdown", "Breakdown"
    CANCELLED = "cancelled", "Cancelled"


def load_status_planner_class(status: str) -> str:
    return f"day-cell--status-{status}"


def load_status_badge_class(status: str) -> str:
    return f"trip-status-badge--{status}"


# Main operational flow shown on load detail (left → right).
LOAD_STATUS_WORKFLOW_SLUGS: tuple[str, ...] = (
    LoadStatus.LOAD_BOOKED,
    LoadStatus.HEADING_TO_PICKUP,
    LoadStatus.AT_PICKUP,
    LoadStatus.LOADED,
    LoadStatus.IN_TRANSIT,
    LoadStatus.AT_DELIVERY,
    LoadStatus.DELIVERED,
    LoadStatus.EMPTY,
)

LOAD_STATUS_WORKFLOW_META: dict[str, dict[str, str]] = {
    LoadStatus.LOAD_BOOKED: {
        "icon": "fa-solid fa-clipboard-list",
        "description": "Load is confirmed and reserved.",
    },
    LoadStatus.HEADING_TO_PICKUP: {
        "icon": "fa-solid fa-truck",
        "description": "Driver is on the way to pickup location.",
    },
    LoadStatus.AT_PICKUP: {
        "icon": "fa-solid fa-warehouse",
        "description": "Driver arrived at pickup location.",
    },
    LoadStatus.LOADED: {
        "icon": "fa-solid fa-boxes-stacked",
        "description": "Load is loaded on the truck.",
    },
    LoadStatus.IN_TRANSIT: {
        "icon": "fa-solid fa-truck-fast",
        "description": "Driver is on the way to delivery.",
    },
    LoadStatus.AT_DELIVERY: {
        "icon": "fa-solid fa-warehouse",
        "description": "Driver arrived at delivery location.",
    },
    LoadStatus.DELIVERED: {
        "icon": "fa-solid fa-circle-check",
        "description": "Load is delivered and unloaded.",
    },
    LoadStatus.EMPTY: {
        "icon": "fa-solid fa-truck",
        "description": "Truck is empty and available for next load.",
    },
}

LOAD_STATUS_OFF_WORKFLOW = frozenset(
    {LoadStatus.LAYOVER, LoadStatus.BREAKDOWN, LoadStatus.CANCELLED}
)


def _workflow_index_for_status(status: str, *, history_to_statuses: list[str] | None = None) -> int | None:
    if status in LOAD_STATUS_WORKFLOW_SLUGS:
        return LOAD_STATUS_WORKFLOW_SLUGS.index(status)
    if not history_to_statuses:
        return None
    for slug in reversed(history_to_statuses):
        if slug in LOAD_STATUS_WORKFLOW_SLUGS:
            return LOAD_STATUS_WORKFLOW_SLUGS.index(slug)
    return None


def workflow_steps_for_load(
    status: str,
    *,
    history_to_statuses: list[str] | None = None,
) -> tuple[list[dict], str | None]:
    """
    Build stepper steps for load detail UI.
    Returns (steps, off_workflow_status_slug).
    """
    labels = dict(LoadStatus.choices)
    current_idx = _workflow_index_for_status(status, history_to_statuses=history_to_statuses)
    off_workflow = status if status in LOAD_STATUS_OFF_WORKFLOW else None

    steps: list[dict] = []
    for i, slug in enumerate(LOAD_STATUS_WORKFLOW_SLUGS):
        meta = LOAD_STATUS_WORKFLOW_META[slug]
        if current_idx is None:
            step_state = "upcoming"
        elif i < current_idx:
            step_state = "done"
        elif i == current_idx and not off_workflow:
            step_state = "current"
        else:
            step_state = "upcoming"

        steps.append(
            {
                "number": i + 1,
                "slug": slug,
                "label": labels.get(slug, slug.replace("_", " ").title()),
                "icon": meta["icon"],
                "description": meta["description"],
                "state": step_state,
                "badge_class": load_status_badge_class(slug),
            }
        )
    return steps, off_workflow
