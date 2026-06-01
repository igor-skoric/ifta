"""Fetch and normalize live GPS from Samsara (locations feed + stats fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .services import SamsaraApiError, SamsaraClient


@dataclass(frozen=True)
class VehicleGpsSnapshot:
    vehicle_id: str
    vehicle_name: str
    latitude: float
    longitude: float
    time: datetime | None
    speed_mph: float | None
    heading_deg: float | None
    address: str
    source: str

    def google_maps_url(self) -> str:
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"

    def coords_display(self) -> str:
        return f"{self.latitude:.5f}, {self.longitude:.5f}"

    def time_display(self) -> str:
        if not self.time:
            return "—"
        local = timezone.localtime(self.time) if timezone.is_aware(self.time) else self.time
        return local.strftime("%b %d, %Y %H:%M %Z").strip()


def _parse_time(raw: Any) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    dt = parse_datetime(raw.strip())
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, dt_timezone.utc)
    return dt


def _parse_float(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _address_from_location(loc: dict) -> str:
    rg = loc.get("reverseGeo")
    if isinstance(rg, dict):
        fmt = rg.get("formattedLocation")
        if isinstance(fmt, str) and fmt.strip():
            return fmt.strip()
    addr = loc.get("address")
    if isinstance(addr, dict):
        name = addr.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return ""


def _snapshot_from_location_event(
    vehicle_id: str,
    vehicle_name: str,
    loc: dict,
    *,
    source: str,
) -> VehicleGpsSnapshot | None:
    lat = _parse_float(loc.get("latitude"))
    lng = _parse_float(loc.get("longitude"))
    if lat is None or lng is None:
        return None
    speed = _parse_float(loc.get("speed"))
    if speed is None:
        speed = _parse_float(loc.get("speedMilesPerHour"))
    heading = _parse_float(loc.get("heading"))
    if heading is None:
        heading = _parse_float(loc.get("headingDegrees"))
    return VehicleGpsSnapshot(
        vehicle_id=str(vehicle_id),
        vehicle_name=vehicle_name or "",
        latitude=lat,
        longitude=lng,
        time=_parse_time(loc.get("time")),
        speed_mph=speed,
        heading_deg=heading,
        address=_address_from_location(loc),
        source=source,
    )


def _parse_locations_feed_vehicle(row: dict) -> VehicleGpsSnapshot | None:
    vid = row.get("id")
    if vid is None:
        return None
    locations = row.get("locations")
    if not isinstance(locations, list) or not locations:
        return None
    loc = locations[-1]
    if not isinstance(loc, dict):
        return None
    name = row.get("name") if isinstance(row.get("name"), str) else ""
    return _snapshot_from_location_event(str(vid), name, loc, source="locations_feed")


def _parse_stats_gps_row(row: dict) -> VehicleGpsSnapshot | None:
    vid = row.get("id")
    if vid is None:
        return None
    gps = row.get("gps")
    if not isinstance(gps, dict):
        return None
    loc = gps
    if isinstance(gps.get("value"), dict):
        merged = {**gps["value"]}
        if gps.get("time") and "time" not in merged:
            merged["time"] = gps.get("time")
        loc = merged
    name = row.get("name") if isinstance(row.get("name"), str) else ""
    return _snapshot_from_location_event(str(vid), name, loc, source="vehicle_stats")


def fetch_vehicle_gps_snapshot(
    samsara_vehicle_id: str,
    *,
    use_cache: bool = True,
    cache_seconds: int | None = None,
) -> VehicleGpsSnapshot | None:
    """Latest GPS for one Samsara vehicle id (API call, optional short cache)."""
    vid = (samsara_vehicle_id or "").strip()
    if not vid:
        return None

    if cache_seconds is None:
        cache_seconds = int(getattr(settings, "SAMSARA_GPS_CACHE_SECONDS", 30))

    cache_key = f"samsara:gps:{vid}"
    if use_cache and cache_seconds > 0:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    client = SamsaraClient()
    snapshot = _fetch_uncached(client, vid)

    if snapshot and use_cache and cache_seconds > 0:
        cache.set(cache_key, snapshot, cache_seconds)
    return snapshot


def _fetch_uncached(client: SamsaraClient, vehicle_id: str) -> VehicleGpsSnapshot | None:
    snapshot = _from_locations_feed(client, vehicle_id)
    if snapshot:
        return snapshot
    return _from_vehicle_stats(client, vehicle_id)


def _from_locations_feed(client: SamsaraClient, vehicle_id: str) -> VehicleGpsSnapshot | None:
    payload = client.get_vehicle_locations_feed(vehicle_ids=[vehicle_id])
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("id")) != str(vehicle_id):
            continue
        parsed = _parse_locations_feed_vehicle(row)
        if parsed:
            return parsed
    return None


def _from_vehicle_stats(client: SamsaraClient, vehicle_id: str) -> VehicleGpsSnapshot | None:
    payload = client.get_vehicle_stats_gps([vehicle_id])
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("id")) != str(vehicle_id):
            continue
        parsed = _parse_stats_gps_row(row)
        if parsed:
            return parsed
    return None


def fetch_vehicle_gps_safe(
    samsara_vehicle_id: str,
    *,
    use_cache: bool = True,
) -> tuple[VehicleGpsSnapshot | None, str | None]:
    """Returns (snapshot, error_message)."""
    try:
        return fetch_vehicle_gps_snapshot(samsara_vehicle_id, use_cache=use_cache), None
    except SamsaraApiError as exc:
        return None, str(exc)
