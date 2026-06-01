import json
import logging
import time
from datetime import datetime, timedelta, timezone as py_timezone

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.utils.dateparse import parse_datetime

from .models import SamsaraDriver, SamsaraSyncRun, SamsaraTrip, SamsaraTripsSyncState, SamsaraVehicle
from .services import SamsaraApiError, SamsaraClient
from .vehicle_display import (
    vehicle_detail_sections,
    vehicle_list_activity,
    vehicle_status_display,
)

logger = logging.getLogger("samsara")

SAMSARA_LIST_PER_PAGE = 50
SAMSARA_DRIVER_TRIPS_PER_PAGE = 50
SAMSARA_VEHICLE_TRIPS_PER_PAGE = 50

VEHICLE_SORT_CHOICES = (
    ("name", "Name A–Z"),
    ("-name", "Name Z–A"),
    ("samsara_id", "Samsara ID ↑"),
    ("-samsara_id", "Samsara ID ↓"),
    ("last_synced_at", "Last sync oldest first"),
    ("-last_synced_at", "Last sync newest first"),
    ("created_at", "Created oldest first"),
    ("-created_at", "Created newest first"),
)
VEHICLE_SORT_ALLOWED = {k for k, _ in VEHICLE_SORT_CHOICES}

DRIVER_SORT_CHOICES = (
    ("name", "Name A–Z"),
    ("-name", "Name Z–A"),
    ("username", "Username A–Z"),
    ("-username", "Username Z–A"),
    ("samsara_id", "Samsara ID ↑"),
    ("-samsara_id", "Samsara ID ↓"),
    ("last_synced_at", "Last sync oldest first"),
    ("-last_synced_at", "Last sync newest first"),
    ("created_at", "Created oldest first"),
    ("-created_at", "Created newest first"),
)
DRIVER_SORT_ALLOWED = {k for k, _ in DRIVER_SORT_CHOICES}


def _list_filter_querystring(request):
    qd = request.GET.copy()
    qd.pop("page", None)
    return qd.urlencode()


TRIP_PAYLOAD_LABELS = (
    ("id", "Trip ID (payload)"),
    ("vehicleId", "Vehicle ID (payload)"),
    ("driverId", "Driver ID (payload)"),
    ("startMs", "Start (UNIX ms)"),
    ("endMs", "End (UNIX ms)"),
    ("startTime", "Start (ISO)"),
    ("endTime", "End (ISO)"),
    ("distanceMeters", "Distance (meters)"),
    ("tollMeters", "Toll distance (m)"),
    ("startOdometer", "Start odometer (m)"),
    ("endOdometer", "End odometer (m)"),
)

TRIP_NESTED_SECTIONS = (
    ("startAddress", "Start address"),
    ("endAddress", "End address"),
)

TRIP_PAYLOAD_HIDDEN_FROM_EXTRA = frozenset(
    {
        "fuelConsumedMl",
        "fuelConsumedMilliliters",
        "startLocation",
        "endLocation",
    }
)

# Samsara fuelConsumedMl → US liquid gallons (231 in³ definition).
_ML_PER_US_GALLON = 3785.411784


def _display_scalar(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return None
    return str(value)


def _display_trip_listish(value, max_items=40, max_len=800):
    if not isinstance(value, list) or not value:
        return None
    chunks = []
    for x in value[:max_items]:
        t = _display_scalar(x)
        chunks.append(t if t is not None else str(x)[:120])
    s = ", ".join(chunks)
    if len(value) > max_items:
        s += f", … (+{len(value) - max_items} more)"
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _trip_nested_section(title, obj):
    if not isinstance(obj, dict):
        return None
    rows = []
    for k, v in sorted(obj.items()):
        st = _display_scalar(v)
        if st is not None:
            rows.append((k, st))
        elif isinstance(v, dict):
            rows.append((k, json.dumps(v, ensure_ascii=False)[:500]))
        elif isinstance(v, list):
            lv = _display_trip_listish(v)
            if lv:
                rows.append((k, lv))
    return {"title": title, "rows": rows} if rows else None


DRIVER_DETAIL_SKIP = frozenset(
    {"eldSettings", "carrierSettings", "attributes", "hosSetting"}
)

DRIVER_PROFILE_ROWS = (
    ("id", "Samsara driver ID"),
    ("name", "Name"),
    ("username", "Username"),
    ("phone", "Phone"),
    ("hasVehicleUnpinningEnabled", "Vehicle unpinning enabled"),
)

DRIVER_LICENSE_ROWS = (
    ("licenseNumber", "License number"),
    ("licenseState", "License state"),
)

DRIVER_REGION_ROWS = (
    ("timezone", "Timezone"),
    ("locale", "Locale"),
)

DRIVER_TIME_ROWS = (
    ("createdAtTime", "Created at (API)"),
    ("updatedAtTime", "Updated at (API)"),
)

# First match wins for driver detail summary "Status" (also excluded from driver extra rows).
DRIVER_STATUS_PAYLOAD_KEYS = (
    "driverActivationStatus",
    "activationStatus",
    "hosStatusType",
    "eldDailyCertification",
    "status",
)


def _rows_from_payload(p, spec):
    rows = []
    if not isinstance(p, dict):
        return rows
    for key, label in spec:
        if key not in p:
            continue
        val = p.get(key)
        if key == "name" and isinstance(val, str):
            val = val.strip()
        text = _display_scalar(val)
        if text is not None:
            rows.append((label, text))
    return rows


def _trip_detail_sections(trip):
    p = trip.raw_payload if isinstance(trip.raw_payload, dict) else {}
    main_keys = {k for k, _ in TRIP_PAYLOAD_LABELS}
    nested_keys = {k for k, _ in TRIP_NESTED_SECTIONS}

    payload_main_rows = _rows_from_payload(p, TRIP_PAYLOAD_LABELS)

    nested_blocks = []
    for key, title in TRIP_NESTED_SECTIONS:
        blk = _trip_nested_section(title, p.get(key))
        if blk:
            nested_blocks.append(blk)

    extra_rows = []
    for key in sorted(p.keys()):
        if key in main_keys or key in nested_keys or key in TRIP_PAYLOAD_HIDDEN_FROM_EXTRA:
            continue
        val = p.get(key)
        st = _display_scalar(val)
        if st is not None:
            extra_rows.append((key, st))
            continue
        if isinstance(val, list):
            ls = _display_trip_listish(val)
            if ls:
                extra_rows.append((key, ls))

    return {
        "payload_main_rows": payload_main_rows,
        "nested_blocks": nested_blocks,
        "extra_rows": extra_rows,
    }


def _trip_extract_lat_lng(obj):
    """Parsira lat/lng iz Samsara-style dicta ili [lat, lng] / [lng, lat] para (preferira imenovana polja)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        lat = obj.get("latitude")
        if lat is None:
            lat = obj.get("lat")
        lng = obj.get("longitude")
        if lng is None:
            lng = obj.get("lng")
        if lng is None:
            lng = obj.get("lon")
        if lat is not None and lng is not None:
            try:
                return (float(lat), float(lng))
            except (TypeError, ValueError):
                return None
    if isinstance(obj, (list, tuple)) and len(obj) >= 2:
        try:
            a, b = float(obj[0]), float(obj[1])
        except (TypeError, ValueError):
            return None
        if abs(b) > 180:
            return None
        if abs(a) > 90:
            return (b, a)
        return (a, b)
    return None


_TRIP_POLYLINE_LIST_KEYS = (
    "gpsTrail",
    "gpsPath",
    "path",
    "polyline",
    "route",
    "coordinates",
    "locations",
)


def _trip_polyline_points(p):
    if not isinstance(p, dict):
        return []
    for key in _TRIP_POLYLINE_LIST_KEYS:
        seq = p.get(key)
        if not isinstance(seq, list) or len(seq) < 2:
            continue
        pts = []
        for item in seq:
            ll = _trip_extract_lat_lng(item)
            if ll:
                pts.append({"lat": ll[0], "lng": ll[1]})
        if len(pts) >= 2:
            return pts
    return []


def _trip_map_context(trip):
    """Podaci za Leaflet: markeri start/kraj + opciona polyline iz raw_payload (bez novih API poziva)."""
    p = trip.raw_payload if isinstance(trip.raw_payload, dict) else {}
    markers = []
    for coord_key, label in (
        ("startCoordinates", "Start"),
        ("endCoordinates", "End"),
    ):
        ll = _trip_extract_lat_lng(p.get(coord_key))
        if ll:
            markers.append({"lat": ll[0], "lng": ll[1], "label": label})
    polyline = _trip_polyline_points(p)
    show = bool(markers or polyline)
    return {
        "trip_map_show": show,
        "trip_map_data": {"markers": markers, "polyline": polyline},
    }


def _carrier_settings_rows(carrier):
    if not isinstance(carrier, dict):
        return []
    order = (
        ("carrierName", "Carrier name"),
        ("dotNumber", "DOT number"),
        ("mainOfficeAddress", "Main office address"),
        ("homeTerminalName", "Home terminal name"),
        ("homeTerminalAddress", "Home terminal address"),
    )
    rows = []
    for key, label in order:
        if key not in carrier:
            rows.append((label, "—"))
            continue
        val = carrier.get(key)
        if val is None or val == "":
            rows.append((label, "—"))
        else:
            text = _display_scalar(val)
            if text is not None:
                rows.append((label, text))
            else:
                rows.append((label, "—"))
    return rows


def _hos_setting_rows(hos):
    if not isinstance(hos, dict):
        return []
    rows = []
    for key, val in sorted(hos.items()):
        text = _display_scalar(val)
        if text is not None:
            label = key.replace("_", " ").title()
            rows.append((label, text))
    return rows


def _driver_attribute_summary(attributes):
    """Samo string vrednosti iz Samsara attributes: label = ime polja, value = tekst (bez ID, bez 'String:')."""
    out = []
    if not isinstance(attributes, list):
        return out
    for attr in attributes:
        if not isinstance(attr, dict):
            continue
        raw_name = attr.get("name")
        if isinstance(raw_name, str):
            raw_name = raw_name.strip()
        if not raw_name:
            continue
        vals = attr.get("stringValues")
        if not isinstance(vals, list) or not vals:
            continue
        pieces = []
        for v in vals:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                pieces.append(s)
        if not pieces:
            continue
        out.append({"label": raw_name, "value": ", ".join(pieces)})
    return out


def _driver_detail_sections(driver):
    p = driver.raw_payload
    if not isinstance(p, dict):
        p = {}

    profile_rows = _rows_from_payload(p, DRIVER_PROFILE_ROWS)
    license_rows = _rows_from_payload(p, DRIVER_LICENSE_ROWS)
    region_rows = _rows_from_payload(p, DRIVER_REGION_ROWS)
    time_rows = _rows_from_payload(p, DRIVER_TIME_ROWS)

    eld = p.get("eldSettings") or {}
    rulesets = eld.get("rulesets") if isinstance(eld, dict) else None
    if not isinstance(rulesets, list):
        rulesets = []
    rulesets = [
        r
        for r in rulesets
        if isinstance(r, dict)
        and any(r.get(k) for k in ("cycle", "shift", "restart", "break"))
    ]

    carrier_rows = []
    if "carrierSettings" in p:
        cset = p.get("carrierSettings")
        carrier_rows = _carrier_settings_rows(cset if isinstance(cset, dict) else {})

    hos_rows = []
    if "hosSetting" in p:
        h = p.get("hosSetting")
        hos_rows = _hos_setting_rows(h if isinstance(h, dict) else {})
    driver_attribute_summary = _driver_attribute_summary(p.get("attributes"))

    handled = (
        {k for k, _ in DRIVER_PROFILE_ROWS}
        | {k for k, _ in DRIVER_LICENSE_ROWS}
        | {k for k, _ in DRIVER_REGION_ROWS}
        | {k for k, _ in DRIVER_TIME_ROWS}
        | DRIVER_DETAIL_SKIP
        | frozenset(DRIVER_STATUS_PAYLOAD_KEYS)
    )
    extra_rows = []
    for key in sorted(p.keys()):
        if key in handled:
            continue
        text = _display_scalar(p.get(key))
        if text is not None:
            extra_rows.append((key, text))

    return {
        "driver_profile_rows": profile_rows,
        "driver_license_rows": license_rows,
        "driver_region_rows": region_rows,
        "driver_time_rows": time_rows,
        "eld_rulesets": rulesets,
        "carrier_rows": carrier_rows,
        "hos_rows": hos_rows,
        "driver_attribute_summary": driver_attribute_summary,
        "driver_extra_rows": extra_rows,
    }


def _record_sync_run(
    *,
    resource,
    success,
    duration_seconds,
    fetched_count=0,
    upserted_count=0,
    error_message="",
):
    SamsaraSyncRun.objects.create(
        resource=resource,
        success=success,
        fetched_count=fetched_count,
        upserted_count=upserted_count,
        duration_seconds=duration_seconds,
        error_message=error_message[:4000] if error_message else "",
    )
    err_snip = (error_message[:200] + "…") if error_message and len(error_message) > 200 else (error_message or "")
    logger.info(
        "sync resource=%s success=%s duration_s=%.3f fetched=%s upserted=%s error=%r",
        resource,
        success,
        duration_seconds,
        fetched_count,
        upserted_count,
        err_snip,
    )


@login_required
def samsara_dashboard(request):
    latest_runs = SamsaraSyncRun.objects.all()[:10]
    trips_sync_watermark_display = None
    try:
        st = SamsaraTripsSyncState.objects.get(pk=1)
        if st.last_query_end_ms is not None:
            trips_sync_watermark_display = datetime.fromtimestamp(
                st.last_query_end_ms / 1000.0, tz=py_timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
    except SamsaraTripsSyncState.DoesNotExist:
        pass
    context = {
        "hide_header_and_footer": False,
        "vehicles_count": SamsaraVehicle.objects.count(),
        "drivers_count": SamsaraDriver.objects.count(),
        "trips_count": SamsaraTrip.objects.count(),
        "latest_runs": latest_runs,
        "trips_sync_watermark_display": trips_sync_watermark_display,
    }
    return render(request, "samsara/dashboard.html", context)


@login_required
def vehicle_list(request):
    q = request.GET.get("q", "").strip()
    name_filter = request.GET.get("name_filter", "").strip()
    external_filter = request.GET.get("external_filter", "").strip()
    sort = request.GET.get("sort", "name")
    if sort not in VEHICLE_SORT_ALLOWED:
        sort = "name"

    qs = SamsaraVehicle.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(samsara_id__icontains=q))
    if name_filter == "named":
        qs = qs.exclude(name="")
    elif name_filter == "unnamed":
        qs = qs.filter(name="")
    if external_filter == "any":
        qs = qs.exclude(external_ids={})
    elif external_filter == "none":
        qs = qs.filter(external_ids={})

    catalog_total = SamsaraVehicle.objects.count()
    filters_active = bool(q or name_filter or external_filter)

    qs = qs.order_by(sort)
    total_count = qs.count()
    paginator = Paginator(qs, SAMSARA_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    _annotate_vehicle_list_rows(page_obj)

    return render(
        request,
        "samsara/vehicle_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "total_count": total_count,
            "catalog_total": catalog_total,
            "filters_active": filters_active,
            "q": q,
            "name_filter": name_filter,
            "external_filter": external_filter,
            "sort": sort,
            "sort_choices": VEHICLE_SORT_CHOICES,
            "filter_querystring": _list_filter_querystring(request),
        },
    )


@login_required
def driver_list(request):
    q = request.GET.get("q", "").strip()
    name_filter = request.GET.get("name_filter", "").strip()
    username_filter = request.GET.get("username_filter", "").strip()
    sort = request.GET.get("sort", "name")
    if sort not in DRIVER_SORT_ALLOWED:
        sort = "name"

    qs = SamsaraDriver.objects.all()
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(username__icontains=q) | Q(samsara_id__icontains=q)
        )
    if name_filter == "named":
        qs = qs.exclude(name="")
    elif name_filter == "unnamed":
        qs = qs.filter(name="")
    if username_filter == "has":
        qs = qs.exclude(username="")
    elif username_filter == "missing":
        qs = qs.filter(username="")

    catalog_total = SamsaraDriver.objects.count()
    filters_active = bool(q or name_filter or username_filter)

    qs = qs.order_by(sort)
    total_count = qs.count()
    paginator = Paginator(qs, SAMSARA_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    _annotate_driver_list_rows(page_obj)

    return render(
        request,
        "samsara/driver_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "total_count": total_count,
            "catalog_total": catalog_total,
            "filters_active": filters_active,
            "q": q,
            "name_filter": name_filter,
            "username_filter": username_filter,
            "sort": sort,
            "sort_choices": DRIVER_SORT_CHOICES,
            "filter_querystring": _list_filter_querystring(request),
        },
    )


def _driver_status_display(driver):
    """Best-effort status from synced driver payload (no extra API call)."""
    p = driver.raw_payload if isinstance(driver.raw_payload, dict) else {}
    for k in DRIVER_STATUS_PAYLOAD_KEYS:
        t = _display_scalar(p.get(k))
        if t and t != "—":
            return t
    return "—"


def _driver_list_activity(row):
    """active | inactive | unknown — for list badge."""
    p = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    for k in ("driverActivationStatus", "activationStatus", "status"):
        v = p.get(k)
        if not isinstance(v, str) or not v.strip():
            continue
        sl = v.strip().lower()
        if any(x in sl for x in ("deactiv", "disabled")) or "inactive" in sl:
            return "inactive"
        if ("activ" in sl and "inactiv" not in sl) or sl in ("enabled", "true", "yes"):
            return "active"
        if sl in ("false", "no"):
            return "inactive"
    return "unknown"


def _annotate_vehicle_list_rows(page_obj):
    for row in page_obj:
        row.list_status_display = vehicle_status_display(row)
        row.list_activity = vehicle_list_activity(row)


def _annotate_driver_list_rows(page_obj):
    for row in page_obj:
        row.list_status_display = _driver_status_display(row)
        row.list_activity = _driver_list_activity(row)


@login_required
def vehicle_detail(request, samsara_id):
    vehicle = get_object_or_404(SamsaraVehicle, samsara_id=samsara_id)
    trips_count = SamsaraTrip.objects.filter(vehicle_samsara_id=vehicle.samsara_id).count()
    sections = vehicle_detail_sections(vehicle)
    return render(
        request,
        "samsara/vehicle_detail.html",
        {
            "hide_header_and_footer": False,
            "vehicle": vehicle,
            "trips_count": trips_count,
            "vehicle_status_display": vehicle_status_display(vehicle),
            **sections,
        },
    )


@login_required
def vehicle_trip_list(request, samsara_id):
    vehicle = get_object_or_404(SamsaraVehicle, samsara_id=samsara_id)
    qs = SamsaraTrip.objects.filter(vehicle_samsara_id=vehicle.samsara_id).order_by("-start_time", "-samsara_id")
    total = qs.count()
    paginator = Paginator(qs, SAMSARA_VEHICLE_TRIPS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    filter_querystring = _list_filter_querystring(request)
    return render(
        request,
        "samsara/vehicle_trips.html",
        {
            "hide_header_and_footer": False,
            "vehicle": vehicle,
            "page_obj": page_obj,
            "total_trips": total,
            "filter_querystring": filter_querystring,
        },
    )


@login_required
def driver_trip_list(request, samsara_id):
    driver = get_object_or_404(SamsaraDriver, samsara_id=samsara_id)
    qs = SamsaraTrip.objects.filter(driver_samsara_id=driver.samsara_id).order_by("-start_time", "-samsara_id")
    total = qs.count()
    paginator = Paginator(qs, SAMSARA_DRIVER_TRIPS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    filter_querystring = _list_filter_querystring(request)
    return render(
        request,
        "samsara/driver_trips.html",
        {
            "hide_header_and_footer": False,
            "driver": driver,
            "page_obj": page_obj,
            "total_trips": total,
            "filter_querystring": filter_querystring,
        },
    )


def _trip_location_display(p, loc_key, addr_key):
    """Human-readable start/end location from startLocation/endLocation or address objects."""
    if not isinstance(p, dict):
        return "—"
    loc = p.get(loc_key)
    if isinstance(loc, str) and loc.strip():
        return loc.strip()
    ad = p.get(addr_key)
    if isinstance(ad, dict):
        parts = []
        for k in ("name", "formattedAddress", "displayName"):
            v = ad.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        inner = ad.get("address")
        if isinstance(inner, dict):
            for k in ("formattedAddress", "address"):
                v = inner.get(k)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
                    break
        elif isinstance(inner, str) and inner.strip():
            parts.append(inner.strip())
        if parts:
            seen = set()
            ordered = []
            for bit in parts:
                if bit not in seen:
                    seen.add(bit)
                    ordered.append(bit)
            return " — ".join(ordered)
    return "—"


def _trip_fuel_display(trip):
    """fuelConsumedMl from payload → US liquid gallons for summary."""
    p = trip.raw_payload if isinstance(trip.raw_payload, dict) else {}
    raw = p.get("fuelConsumedMl")
    if raw is None:
        raw = p.get("fuelConsumedMilliliters")
    if raw is None:
        return "—"
    try:
        ml = float(raw)
    except (TypeError, ValueError):
        return "—"
    if ml <= 0:
        return "—"
    gal = ml / _ML_PER_US_GALLON
    if gal >= 100:
        return f"{gal:.1f} gal"
    return f"{gal:.2f} gal"


def _trip_duration_display(trip):
    if not trip.start_time or not trip.end_time:
        return "—"
    delta = trip.end_time - trip.start_time
    sec = int(delta.total_seconds())
    if sec < 0:
        return "—"
    if sec >= 86400:
        d, sec = divmod(sec, 86400)
        h, sec = divmod(sec, 3600)
        m, _ = divmod(sec, 60)
        return f"{d}d {h}h {m}m"
    h, sec = divmod(sec, 3600)
    m, s = divmod(sec, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


@login_required
def trip_detail(request, samsara_id):
    trip = get_object_or_404(SamsaraTrip, samsara_id=samsara_id)
    sections = _trip_detail_sections(trip)
    map_ctx = _trip_map_context(trip)
    p = trip.raw_payload if isinstance(trip.raw_payload, dict) else {}
    return render(
        request,
        "samsara/trip_detail.html",
        {
            "hide_header_and_footer": False,
            "trip": trip,
            "trip_duration_display": _trip_duration_display(trip),
            "trip_fuel_display": _trip_fuel_display(trip),
            "trip_start_location": _trip_location_display(p, "startLocation", "startAddress"),
            "trip_end_location": _trip_location_display(p, "endLocation", "endAddress"),
            **sections,
            **map_ctx,
        },
    )


@login_required
def driver_detail(request, samsara_id):
    driver = get_object_or_404(SamsaraDriver, samsara_id=samsara_id)
    trips_count = SamsaraTrip.objects.filter(driver_samsara_id=driver.samsara_id).count()
    sections = _driver_detail_sections(driver)
    return render(
        request,
        "samsara/driver_detail.html",
        {
            "hide_header_and_footer": False,
            "driver": driver,
            "trips_count": trips_count,
            "driver_status_display": _driver_status_display(driver),
            **sections,
        },
    )


@require_POST
@login_required
def sync_vehicles(request):
    t0 = time.perf_counter()
    try:
        client = SamsaraClient()
        vehicles = client.list_vehicles()
        upserted = 0
        for item in vehicles:
            vehicle_id = str(item.get("id") or "")
            if not vehicle_id:
                continue
            name = item.get("name") or item.get("vehicleName") or ""
            external_ids = item.get("externalIds") or {}
            _, created = SamsaraVehicle.objects.update_or_create(
                samsara_id=vehicle_id,
                defaults={"name": name, "external_ids": external_ids, "raw_payload": item},
            )
            upserted += 1 if created else 1
        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="vehicles",
            success=True,
            duration_seconds=elapsed,
            fetched_count=len(vehicles),
            upserted_count=upserted,
        )
    except SamsaraApiError as exc:
        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="vehicles",
            success=False,
            duration_seconds=elapsed,
            error_message=str(exc),
        )
    return redirect("samsara:dashboard")


@require_POST
@login_required
def sync_drivers(request):
    t0 = time.perf_counter()
    try:
        client = SamsaraClient()
        drivers = client.list_drivers()
        upserted = 0
        for item in drivers:
            driver_id = str(item.get("id") or "")
            if not driver_id:
                continue
            first_name = item.get("firstName") or ""
            last_name = item.get("lastName") or ""
            name = (f"{first_name} {last_name}").strip() or item.get("name") or ""
            username = item.get("username") or ""
            _, created = SamsaraDriver.objects.update_or_create(
                samsara_id=driver_id,
                defaults={"name": name, "username": username, "raw_payload": item},
            )
            upserted += 1 if created else 1
        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="drivers",
            success=True,
            duration_seconds=elapsed,
            fetched_count=len(drivers),
            upserted_count=upserted,
        )
    except SamsaraApiError as exc:
        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="drivers",
            success=False,
            duration_seconds=elapsed,
            error_message=str(exc),
        )
    return redirect("samsara:dashboard")


@require_POST
@login_required
def sync_trips(request):
    t0 = time.perf_counter()
    full_reset = request.POST.get("full_trips_sync")
    try:
        state = SamsaraTripsSyncState.objects.filter(pk=1).first()
        effective_last = None if full_reset else (state.last_query_end_ms if state else None)

        end_ms = int(timezone.now().timestamp() * 1000)
        overlap_ms = int(getattr(settings, "SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS", 2 * 3600 * 1000))
        days_back = int(getattr(settings, "SAMSARA_TRIPS_DAYS_BACK", 14))

        if effective_last is None:
            start_ms = end_ms - int(timedelta(days=days_back).total_seconds() * 1000)
        else:
            start_ms = max(0, int(effective_last) - overlap_ms)

        if start_ms >= end_ms:
            trips = []
            logger.info("trips sync skipped empty window start_ms=%s end_ms=%s", start_ms, end_ms)
        else:
            logger.info(
                "trips sync window start_ms=%s end_ms=%s span_days=%.2f full_resync_window=%s",
                start_ms,
                end_ms,
                (end_ms - start_ms) / (86400 * 1000),
                bool(full_reset),
            )
            client = SamsaraClient()
            trips = client.list_trips(start_ms=start_ms, end_ms=end_ms)

        upserted = 0
        with transaction.atomic():
            for item in trips:
                trip_id = str(item.get("id") or "")
                if not trip_id:
                    continue
                vehicle_id = str(item.get("vehicleId") or item.get("vehicle", {}).get("id") or "")
                driver_id = str(item.get("driverId") or item.get("driver", {}).get("id") or "")
                start_time = parse_datetime(item.get("startTime") or "") if item.get("startTime") else None
                end_time = parse_datetime(item.get("endTime") or "") if item.get("endTime") else None
                distance_meters = float(item.get("distanceMeters") or item.get("distance") or 0)
                SamsaraTrip.objects.update_or_create(
                    samsara_id=trip_id,
                    defaults={
                        "vehicle_samsara_id": vehicle_id,
                        "driver_samsara_id": driver_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "distance_meters": distance_meters,
                        "raw_payload": item,
                    },
                )
                upserted += 1
            SamsaraTripsSyncState.objects.update_or_create(
                pk=1,
                defaults={"last_query_end_ms": end_ms},
            )

        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="trips",
            success=True,
            duration_seconds=elapsed,
            fetched_count=len(trips),
            upserted_count=upserted,
        )
    except (SamsaraApiError, ValueError, TypeError) as exc:
        elapsed = time.perf_counter() - t0
        _record_sync_run(
            resource="trips",
            success=False,
            duration_seconds=elapsed,
            error_message=str(exc),
        )
    return redirect("samsara:dashboard")
