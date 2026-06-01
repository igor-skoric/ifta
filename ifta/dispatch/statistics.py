"""Aggregate dispatch load metrics by dispatcher and driver."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from office.models import OfficeDirectoryEmployee

from .load_docs_status import PODStatus, RCStatus
from .load_status import LoadStatus
from .models import DispatchDriver, DispatchLoad

ViewMode = Literal["dispatcher", "driver"]
Period = Literal["this_week", "last_week", "this_month", "this_year"]

PERIOD_CHOICES: tuple[tuple[str, str], ...] = (
    ("this_week", "This week"),
    ("last_week", "Last week"),
    ("this_month", "This month"),
    ("this_year", "This year"),
)
VALID_PERIODS = frozenset(k for k, _ in PERIOD_CHOICES)
DEFAULT_PERIOD: Period = "this_month"

ACTIVE_STATUSES = frozenset(
    {
        LoadStatus.LOAD_BOOKED,
        LoadStatus.HEADING_TO_PICKUP,
        LoadStatus.AT_PICKUP,
        LoadStatus.LOADED,
        LoadStatus.IN_TRANSIT,
        LoadStatus.AT_DELIVERY,
        LoadStatus.EMPTY,
        LoadStatus.LAYOVER,
        LoadStatus.BREAKDOWN,
    }
)


@dataclass(frozen=True)
class FleetTotals:
    load_count: int = 0
    delivered_count: int = 0
    cancelled_count: int = 0
    active_count: int = 0
    unassigned_count: int = 0
    total_miles: int = 0
    total_linehaul: Decimal = Decimal("0")
    pod_open_count: int = 0
    rc_open_count: int = 0

    @property
    def avg_rate_per_mile(self) -> Decimal | None:
        if self.total_miles > 0 and self.total_linehaul:
            return self.total_linehaul / Decimal(self.total_miles)
        return None


@dataclass(frozen=True)
class DispatcherStatsRow:
    dispatcher_id: int | None
    name: str
    driver_count: int
    load_count: int
    delivered_count: int
    cancelled_count: int
    active_count: int
    total_miles: int
    total_linehaul: Decimal
    pod_open_count: int
    rc_open_count: int

    @property
    def avg_rate_per_mile(self) -> Decimal | None:
        if self.total_miles > 0 and self.total_linehaul:
            return self.total_linehaul / Decimal(self.total_miles)
        return None


@dataclass(frozen=True)
class DriverStatsRow:
    driver_id: int
    name: str
    dispatcher_name: str
    load_count: int
    delivered_count: int
    cancelled_count: int
    active_count: int
    total_miles: int
    total_linehaul: Decimal
    pod_open_count: int
    rc_open_count: int

    @property
    def avg_rate_per_mile(self) -> Decimal | None:
        if self.total_miles > 0 and self.total_linehaul:
            return self.total_linehaul / Decimal(self.total_miles)
        return None


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _last_day_of_month(d: date) -> date:
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def date_range_for_period(period: str) -> tuple[date, date]:
    """Full calendar period (week / month / year), not truncated to today."""
    today = timezone.localdate()
    if period == "this_week":
        monday = _monday_of_week(today)
        return monday, monday + timedelta(days=6)
    if period == "last_week":
        monday = _monday_of_week(today) - timedelta(days=7)
        return monday, monday + timedelta(days=6)
    if period == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    start = today.replace(day=1)
    return start, _last_day_of_month(today)


def parse_statistics_filters(
    request,
) -> tuple[ViewMode, date, date, str, str]:
    """Returns (view, date_from, date_to, dispatcher_filter_pk, period)."""
    view = (request.GET.get("view") or "dispatcher").strip().lower()
    if view not in ("dispatcher", "driver"):
        view = "dispatcher"

    period = (request.GET.get("period") or DEFAULT_PERIOD).strip().lower()
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD
    date_from, date_to = date_range_for_period(period)

    dispatcher = (request.GET.get("dispatcher") or "").strip()
    if not dispatcher.isdigit():
        dispatcher = ""
    return view, date_from, date_to, dispatcher, period


def loads_in_range(date_from: date, date_to: date) -> QuerySet[DispatchLoad]:
    return DispatchLoad.objects.filter(
        planner_date__gte=date_from,
        planner_date__lte=date_to,
    ).select_related("driver", "driver__dispatcher")


def _load_aggregates():
    return {
        "load_count": Count("id"),
        "delivered_count": Count("id", filter=Q(status=LoadStatus.DELIVERED)),
        "cancelled_count": Count("id", filter=Q(status=LoadStatus.CANCELLED)),
        "active_count": Count("id", filter=Q(status__in=ACTIVE_STATUSES)),
        "total_miles": Coalesce(Sum("loaded_miles"), 0),
        "total_linehaul": Coalesce(Sum("linehaul_amount"), Decimal("0")),
        "pod_open_count": Count(
            "id",
            filter=~Q(pod_status=PODStatus.DELIVERED),
        ),
        "rc_open_count": Count(
            "id",
            filter=Q(rc_status=RCStatus.NOT_SENT),
        ),
    }


def build_fleet_totals(loads: QuerySet[DispatchLoad]) -> FleetTotals:
    agg = loads.aggregate(
        **_load_aggregates(),
        unassigned_count=Count("id", filter=Q(driver_id__isnull=True)),
    )
    return FleetTotals(
        load_count=agg["load_count"] or 0,
        delivered_count=agg["delivered_count"] or 0,
        cancelled_count=agg["cancelled_count"] or 0,
        active_count=agg["active_count"] or 0,
        unassigned_count=agg["unassigned_count"] or 0,
        total_miles=int(agg["total_miles"] or 0),
        total_linehaul=agg["total_linehaul"] or Decimal("0"),
        pod_open_count=agg["pod_open_count"] or 0,
        rc_open_count=agg["rc_open_count"] or 0,
    )


def build_dispatcher_rows(
    loads: QuerySet[DispatchLoad],
    *,
    dispatcher_filter: str = "",
) -> list[DispatcherStatsRow]:
    qs = loads.filter(driver_id__isnull=False, driver__dispatcher_id__isnull=False)
    if dispatcher_filter:
        qs = qs.filter(driver__dispatcher_id=int(dispatcher_filter))

    grouped = (
        qs.values(
            "driver__dispatcher_id",
            "driver__dispatcher__first_name",
            "driver__dispatcher__last_name",
        )
        .annotate(
            **_load_aggregates(),
            driver_count=Count("driver_id", distinct=True),
        )
        .order_by("driver__dispatcher__last_name", "driver__dispatcher__first_name")
    )

    rows: list[DispatcherStatsRow] = []
    for row in grouped:
        first = (row.get("driver__dispatcher__first_name") or "").strip()
        last = (row.get("driver__dispatcher__last_name") or "").strip()
        name = f"{first} {last}".strip() or "—"
        rows.append(
            DispatcherStatsRow(
                dispatcher_id=row["driver__dispatcher_id"],
                name=name,
                driver_count=row["driver_count"] or 0,
                load_count=row["load_count"] or 0,
                delivered_count=row["delivered_count"] or 0,
                cancelled_count=row["cancelled_count"] or 0,
                active_count=row["active_count"] or 0,
                total_miles=int(row["total_miles"] or 0),
                total_linehaul=row["total_linehaul"] or Decimal("0"),
                pod_open_count=row["pod_open_count"] or 0,
                rc_open_count=row["rc_open_count"] or 0,
            )
        )

    unassigned = loads.filter(Q(driver_id__isnull=True) | Q(driver__dispatcher_id__isnull=True))
    if unassigned.exists() and not dispatcher_filter:
        agg = unassigned.aggregate(**_load_aggregates())
        rows.append(
            DispatcherStatsRow(
                dispatcher_id=None,
                name="Unassigned / no dispatcher",
                driver_count=unassigned.filter(driver_id__isnull=False).values("driver_id").distinct().count(),
                load_count=agg["load_count"] or 0,
                delivered_count=agg["delivered_count"] or 0,
                cancelled_count=agg["cancelled_count"] or 0,
                active_count=agg["active_count"] or 0,
                total_miles=int(agg["total_miles"] or 0),
                total_linehaul=agg["total_linehaul"] or Decimal("0"),
                pod_open_count=agg["pod_open_count"] or 0,
                rc_open_count=agg["rc_open_count"] or 0,
            )
        )
    return rows


def build_driver_rows(
    loads: QuerySet[DispatchLoad],
    *,
    dispatcher_filter: str = "",
) -> list[DriverStatsRow]:
    qs = loads.filter(driver_id__isnull=False)
    if dispatcher_filter:
        qs = qs.filter(driver__dispatcher_id=int(dispatcher_filter))

    grouped = (
        qs.values(
            "driver_id",
            "driver__first_name",
            "driver__last_name",
            "driver__dispatcher__first_name",
            "driver__dispatcher__last_name",
        )
        .annotate(**_load_aggregates())
        .order_by("-load_count", "driver__last_name", "driver__first_name")
    )

    rows: list[DriverStatsRow] = []
    for row in grouped:
        dfirst = (row.get("driver__first_name") or "").strip()
        dlast = (row.get("driver__last_name") or "").strip()
        disp_first = (row.get("driver__dispatcher__first_name") or "").strip()
        disp_last = (row.get("driver__dispatcher__last_name") or "").strip()
        disp_name = f"{disp_first} {disp_last}".strip() or "—"
        rows.append(
            DriverStatsRow(
                driver_id=row["driver_id"],
                name=f"{dfirst} {dlast}".strip() or f"Driver #{row['driver_id']}",
                dispatcher_name=disp_name,
                load_count=row["load_count"] or 0,
                delivered_count=row["delivered_count"] or 0,
                cancelled_count=row["cancelled_count"] or 0,
                active_count=row["active_count"] or 0,
                total_miles=int(row["total_miles"] or 0),
                total_linehaul=row["total_linehaul"] or Decimal("0"),
                pod_open_count=row["pod_open_count"] or 0,
                rc_open_count=row["rc_open_count"] or 0,
            )
        )
    return rows


def dispatcher_choices() -> list[OfficeDirectoryEmployee]:
    return list(
        OfficeDirectoryEmployee.objects.filter(is_active=True, is_dispatcher=True).order_by(
            "last_name", "first_name"
        )
    )
