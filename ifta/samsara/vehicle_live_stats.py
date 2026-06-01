"""Live telematics snapshot (fuel, engine, faults) from Samsara vehicle stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .services import SamsaraApiError, SamsaraClient

# Request types (Samsara query param) vs response keys (often singular on snapshot).
LIVE_STAT_TYPES = ("fuelPercents", "engineStates", "faultCodes")
FUEL_RESPONSE_KEYS = ("fuelPercent", "fuelPercents")
ENGINE_RESPONSE_KEYS = ("engineState", "engineStates")
FAULT_RESPONSE_KEYS = ("faultCodes",)


@dataclass(frozen=True)
class VehicleLiveStats:
    fuel_percent: float | None = None
    fuel_updated_display: str = ""
    engine_state: str = ""
    engine_updated_display: str = ""
    fault_lines: list[str] = field(default_factory=list)
    has_active_faults: bool = False


def _parse_time_display(raw) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    dt = parse_datetime(raw.strip())
    if dt is None:
        return ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    local = timezone.localtime(dt)
    return local.strftime("%b %d, %Y %H:%M %Z").strip()


def _read_stat_field(row: dict, *keys: str) -> tuple[object | None, str]:
    """Read a stat from a vehicle stats row (list series or single {time,value} blob)."""
    raw = None
    for key in keys:
        candidate = row.get(key)
        if candidate is not None:
            raw = candidate
            break
    if raw is None:
        return None, ""

    if isinstance(raw, list):
        if not raw:
            return None, ""
        raw = raw[-1]

    if not isinstance(raw, dict):
        return raw, ""

    time_display = _parse_time_display(raw.get("time"))
    if "value" in raw:
        return raw.get("value"), time_display
    return raw, time_display


def _fault_lines_from_value(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, dict):
        return []

    lines: list[str] = []

    def _append_dtc(dtc: dict) -> None:
        if not isinstance(dtc, dict):
            return
        spn = (dtc.get("spnDescription") or dtc.get("dtcDescription") or "").strip()
        fmi = (dtc.get("fmiDescription") or "").strip()
        code = str(dtc.get("dtcId") or dtc.get("spnId") or "").strip()
        if spn and fmi:
            lines.append(f"{spn} ({fmi})")
        elif spn:
            lines.append(spn)
        elif code:
            lines.append(code)

    def _walk(obj) -> None:
        if isinstance(obj, dict):
            dtcs = obj.get("diagnosticTroubleCodes")
            if isinstance(dtcs, list):
                for dtc in dtcs[:12]:
                    _append_dtc(dtc)
            for key, nested in obj.items():
                if key in ("diagnosticTroubleCodes", "checkEngineLights"):
                    continue
                if isinstance(nested, (dict, list)):
                    _walk(nested)
        elif isinstance(obj, list):
            for item in obj[:12]:
                _walk(item)

    for bucket_key in ("j1939", "obdii", "passenger", "diagnosticTroubleCodes"):
        bucket = value.get(bucket_key)
        if bucket:
            _walk(bucket)

    if not lines:
        _walk(value)

    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out[:8]


def parse_vehicle_live_stats_row(row: dict) -> VehicleLiveStats:
    fuel_val, fuel_time = _read_stat_field(row, *FUEL_RESPONSE_KEYS)
    fuel_percent = None
    if fuel_val is not None:
        try:
            fuel_percent = float(fuel_val)
        except (TypeError, ValueError):
            fuel_percent = None

    engine_val, engine_time = _read_stat_field(row, *ENGINE_RESPONSE_KEYS)
    engine_state = str(engine_val).strip() if engine_val is not None else ""

    fault_val, _fault_time = _read_stat_field(row, *FAULT_RESPONSE_KEYS)
    fault_lines = _fault_lines_from_value(fault_val)

    return VehicleLiveStats(
        fuel_percent=fuel_percent,
        fuel_updated_display=fuel_time,
        engine_state=engine_state,
        engine_updated_display=engine_time,
        fault_lines=fault_lines,
        has_active_faults=bool(fault_lines),
    )


def fetch_vehicle_live_stats(vehicle_id: str) -> VehicleLiveStats | None:
    vid = (vehicle_id or "").strip()
    if not vid:
        return None
    client = SamsaraClient()
    payload = client.get_vehicle_stats([vid], LIVE_STAT_TYPES)
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("id")) != str(vid):
            continue
        return parse_vehicle_live_stats_row(row)
    return VehicleLiveStats()


def fetch_vehicle_live_stats_safe(
    vehicle_id: str,
) -> tuple[VehicleLiveStats | None, str | None]:
    try:
        return fetch_vehicle_live_stats(vehicle_id), None
    except SamsaraApiError as exc:
        return None, str(exc)
