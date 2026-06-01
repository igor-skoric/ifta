"""Backward-compatible aliases (CSS classes still use trip-status-* prefix)."""

from .load_status import (
    LOAD_STATUS_STYLES,
    LoadStatus,
    load_status_badge_class,
    load_status_planner_class,
)

TRIP_STATUS_STYLES = LOAD_STATUS_STYLES
trip_status_planner_class = load_status_planner_class
trip_status_badge_class = load_status_badge_class
