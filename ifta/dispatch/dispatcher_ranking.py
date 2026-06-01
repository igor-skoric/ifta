"""Dispatcher leaderboard — normalized metrics and composite ranking."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from office.models import OfficeDirectoryEmployee

from .load_docs_status import PODStatus, RCStatus
from .load_status import LoadStatus
from .models import DispatchDriver, DispatchLoad
from .statistics import (
    ACTIVE_STATUSES,
    DEFAULT_PERIOD,
    PERIOD_CHOICES,
    VALID_PERIODS,
    _load_aggregates,
)

# Weights for composite score (must sum to 1.0)
SCORE_WEIGHTS: dict[str, float] = {
    "delivery_rate": 0.22,
    "loads_per_roster": 0.20,
    "linehaul_per_roster": 0.16,
    "avg_rpm": 0.14,
    "doc_compliance": 0.14,
    "driver_utilization": 0.08,
    "cancel_inverse": 0.06,
}

SORT_CHOICES: tuple[tuple[str, str], ...] = (
    ("overall_score", "Overall score"),
    ("loads_per_roster", "Loads / driver"),
    ("linehaul_per_roster", "Linehaul / driver"),
    ("delivery_rate", "Delivery rate"),
    ("avg_rpm", "Avg $/mi"),
    ("doc_compliance", "Doc compliance"),
    ("load_count", "Total loads"),
)
VALID_SORTS = frozenset(k for k, _ in SORT_CHOICES)


@dataclass
class DispatcherLeaderboardRow:
    dispatcher_id: int
    name: str
    employee_id: str
    roster_size: int
    drivers_active: int
    load_count: int
    delivered_count: int
    cancelled_count: int
    active_count: int
    total_miles: int
    total_linehaul: Decimal
    pod_open_count: int
    rc_open_count: int
    loads_per_roster: float = 0.0
    miles_per_roster: float = 0.0
    linehaul_per_roster: Decimal = field(default_factory=lambda: Decimal("0"))
    delivery_rate: float = 0.0
    cancel_rate: float = 0.0
    pod_compliance: float = 0.0
    rc_compliance: float = 0.0
    doc_compliance: float = 0.0
    driver_utilization: float = 0.0
    avg_rpm: Decimal | None = None
    avg_linehaul_per_load: Decimal | None = None
    overall_score: float = 0.0
    overall_rank: int = 0
    ranks: dict[str, int] = field(default_factory=dict)
    top_in: list[str] = field(default_factory=list)


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _last_day_of_month(d: date) -> date:
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def date_range_for_period(period: str) -> tuple[date, date]:
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


def parse_ranking_params(request) -> tuple[str, date, date, str]:
    period = (request.GET.get("period") or DEFAULT_PERIOD).strip().lower()
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD
    date_from, date_to = date_range_for_period(period)

    sort = (request.GET.get("sort") or "overall_score").strip().lower()
    if sort not in VALID_SORTS:
        sort = "overall_score"
    return period, date_from, date_to, sort


def loads_in_range(date_from: date, date_to: date) -> QuerySet[DispatchLoad]:
    return DispatchLoad.objects.filter(
        planner_date__gte=date_from,
        planner_date__lte=date_to,
    ).select_related("driver", "driver__dispatcher")


def _roster_counts() -> dict[int, int]:
    return {
        row["dispatcher_id"]: row["c"]
        for row in DispatchDriver.objects.filter(is_active=True, dispatcher_id__isnull=False)
        .values("dispatcher_id")
        .annotate(c=Count("id"))
    }


def build_leaderboard_rows(loads: QuerySet[DispatchLoad]) -> list[DispatcherLeaderboardRow]:
    roster = _roster_counts()
    dispatchers = OfficeDirectoryEmployee.objects.filter(is_active=True, is_dispatcher=True).order_by(
        "last_name", "first_name"
    )

    grouped = {
        row["driver__dispatcher_id"]: row
        for row in loads.filter(driver_id__isnull=False, driver__dispatcher_id__isnull=False)
        .values("driver__dispatcher_id")
        .annotate(
            **_load_aggregates(),
            drivers_active=Count("driver_id", distinct=True),
        )
    }

    rows: list[DispatcherLeaderboardRow] = []
    for disp in dispatchers:
        agg = grouped.get(disp.pk, {})
        roster_size = roster.get(disp.pk, 0)
        load_count = agg.get("load_count") or 0
        drivers_active = agg.get("drivers_active") or 0
        delivered = agg.get("delivered_count") or 0
        cancelled = agg.get("cancelled_count") or 0
        total_miles = int(agg.get("total_miles") or 0)
        total_linehaul = agg.get("total_linehaul") or Decimal("0")
        pod_open = agg.get("pod_open_count") or 0
        rc_open = agg.get("rc_open_count") or 0

        roster_denom = max(roster_size, 1)
        loads_per_roster = load_count / roster_denom
        miles_per_roster = total_miles / roster_denom
        linehaul_per_roster = total_linehaul / Decimal(roster_denom)

        delivery_rate = (100.0 * delivered / load_count) if load_count else 0.0
        cancel_rate = (100.0 * cancelled / load_count) if load_count else 0.0
        pod_compliance = (100.0 * (load_count - pod_open) / load_count) if load_count else 0.0
        rc_compliance = (100.0 * (load_count - rc_open) / load_count) if load_count else 0.0
        doc_compliance = (pod_compliance + rc_compliance) / 2.0 if load_count else 0.0
        driver_utilization = (100.0 * drivers_active / roster_size) if roster_size else 0.0

        avg_rpm = None
        if total_miles > 0 and total_linehaul:
            avg_rpm = total_linehaul / Decimal(total_miles)
        avg_linehaul = (total_linehaul / Decimal(load_count)) if load_count and total_linehaul else None

        rows.append(
            DispatcherLeaderboardRow(
                dispatcher_id=disp.pk,
                name=f"{disp.first_name} {disp.last_name}".strip(),
                employee_id=disp.employee_id or "",
                roster_size=roster_size,
                drivers_active=drivers_active,
                load_count=load_count,
                delivered_count=delivered,
                cancelled_count=cancelled,
                active_count=agg.get("active_count") or 0,
                total_miles=total_miles,
                total_linehaul=total_linehaul,
                pod_open_count=pod_open,
                rc_open_count=rc_open,
                loads_per_roster=loads_per_roster,
                miles_per_roster=miles_per_roster,
                linehaul_per_roster=linehaul_per_roster,
                delivery_rate=delivery_rate,
                cancel_rate=cancel_rate,
                pod_compliance=pod_compliance,
                rc_compliance=rc_compliance,
                doc_compliance=doc_compliance,
                driver_utilization=driver_utilization,
                avg_rpm=avg_rpm,
                avg_linehaul_per_load=avg_linehaul,
            )
        )

    _apply_rankings(rows)
    return rows


def _eligible(rows: list[DispatcherLeaderboardRow]) -> list[DispatcherLeaderboardRow]:
    return [r for r in rows if r.load_count >= 1 and r.roster_size >= 1]


def _normalize(values: list[float], higher_better: bool) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    scaled = [(v - lo) / (hi - lo) for v in values]
    if not higher_better:
        scaled = [1.0 - s for s in scaled]
    return scaled


def _metric_value(row: DispatcherLeaderboardRow, key: str) -> float | None:
    if key == "loads_per_roster":
        return row.loads_per_roster
    if key == "linehaul_per_roster":
        return float(row.linehaul_per_roster)
    if key == "delivery_rate":
        return row.delivery_rate
    if key == "avg_rpm":
        return float(row.avg_rpm) if row.avg_rpm is not None else None
    if key == "doc_compliance":
        return row.doc_compliance
    if key == "driver_utilization":
        return row.driver_utilization
    if key == "cancel_inverse":
        return 100.0 - row.cancel_rate if row.load_count else None
    if key == "load_count":
        return float(row.load_count)
    return None


def _rank_metric(
    rows: list[DispatcherLeaderboardRow],
    key: str,
    *,
    higher_better: bool = True,
) -> dict[int, int]:
    eligible = _eligible(rows)
    indexed: list[tuple[int, float]] = []
    for row in eligible:
        val = _metric_value(row, key)
        if val is not None:
            indexed.append((row.dispatcher_id, val))
    indexed.sort(key=lambda x: x[1], reverse=higher_better)
    return {disp_id: rank for rank, (disp_id, _) in enumerate(indexed, 1)}


def _apply_rankings(rows: list[DispatcherLeaderboardRow]) -> None:
    eligible = _eligible(rows)
    if not eligible:
        return

    metric_keys = list(SCORE_WEIGHTS.keys())
    rank_maps = {key: _rank_metric(rows, key, higher_better=True) for key in metric_keys}

    # Per-metric ranks on each row
    display_rank_keys = [
        ("overall_score", True),
        ("loads_per_roster", True),
        ("linehaul_per_roster", True),
        ("delivery_rate", True),
        ("avg_rpm", True),
        ("doc_compliance", True),
        ("driver_utilization", True),
        ("load_count", True),
        ("cancel_rate", False),
    ]
    all_rank_maps: dict[str, dict[int, int]] = {}
    labels = {
        "loads_per_roster": "Loads/driver",
        "linehaul_per_roster": "Linehaul/driver",
        "delivery_rate": "Delivery %",
        "avg_rpm": "$/mi",
        "doc_compliance": "Docs",
        "driver_utilization": "Utilization",
        "load_count": "Volume",
        "cancel_rate": "Low cancel",
    }
    for key, higher in display_rank_keys:
        all_rank_maps[key] = _rank_metric(rows, key, higher_better=higher)

    score_by_id: dict[int, float] = {}
    for row in eligible:
        parts: list[float] = []
        for key, weight in SCORE_WEIGHTS.items():
            vals = []
            for r in eligible:
                v = _metric_value(r, key)
                if v is not None:
                    vals.append((r.dispatcher_id, v))
            if not vals:
                continue
            raw = [v for _, v in vals]
            normed = _normalize(raw, higher_better=True)
            id_to_norm = {disp_id: normed[i] for i, (disp_id, _) in enumerate(vals)}
            parts.append(weight * id_to_norm.get(row.dispatcher_id, 0.0))
        score_by_id[row.dispatcher_id] = round(sum(parts) * 100.0, 1)

    score_rank = sorted(score_by_id.items(), key=lambda x: x[1], reverse=True)
    score_rank_map = {disp_id: i for i, (disp_id, _) in enumerate(score_rank, 1)}

    for row in rows:
        row.ranks = {key: all_rank_maps.get(key, {}).get(row.dispatcher_id, 0) for key in all_rank_maps}
        row.ranks["overall_score"] = score_rank_map.get(row.dispatcher_id, 0)
        row.overall_score = score_by_id.get(row.dispatcher_id, 0.0)
        row.overall_rank = score_rank_map.get(row.dispatcher_id, 0)

        badges: list[str] = []
        for key, label in labels.items():
            if row.ranks.get(key) == 1 and row.load_count >= 1:
                badges.append(label)
        row.top_in = badges[:4]

    rows.sort(key=lambda r: (r.overall_rank or 9999, r.name.lower()))


def sort_leaderboard(
    rows: list[DispatcherLeaderboardRow], sort_key: str
) -> list[DispatcherLeaderboardRow]:
    def sort_val(r: DispatcherLeaderboardRow) -> float:
        v = _metric_value(r, sort_key)
        if v is not None:
            return v
        if sort_key == "overall_score":
            return r.overall_score
        return -1.0

    return sorted(rows, key=sort_val, reverse=True)


def period_label(period: str) -> str:
    for key, label in PERIOD_CHOICES:
        if key == period:
            return label
    return period.replace("_", " ").title()
