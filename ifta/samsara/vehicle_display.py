"""Structured display of synced Samsara vehicle payloads (no raw JSON in templates)."""

from __future__ import annotations

VEHICLE_DETAIL_FIELD_LABELS = (
    ("id", "Samsara asset ID"),
    ("name", "Name"),
    ("make", "Make"),
    ("model", "Model"),
    ("year", "Year"),
    ("vin", "VIN"),
    ("serial", "Serial"),
    ("cameraSerial", "Camera serial"),
    ("esn", "ESN"),
    ("notes", "Notes"),
    ("harshAccelerationSettingType", "Harsh acceleration setting"),
    ("vehicleRegulationMode", "Vehicle regulation mode"),
    ("createdAtTime", "Created at (API)"),
    ("updatedAtTime", "Updated at (API)"),
)

VEHICLE_DETAIL_NESTED_SKIP = frozenset({"gateway", "staticAssignedDriver", "tags", "externalIds"})

VEHICLE_DETAIL_EXTRA_SKIP = frozenset(
    {
        "engineState",
        "vehicleEngineState",
        "motionStatus",
    }
)


def display_scalar(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return None
    return str(value)


def vehicle_status_display(vehicle) -> str:
    """Best-effort status from synced vehicle payload (no extra API call)."""
    p = vehicle.raw_payload if isinstance(vehicle.raw_payload, dict) else {}
    for k in ("engineState", "vehicleEngineState", "motionStatus"):
        t = display_scalar(p.get(k))
        if t and t != "—":
            return t
    g = p.get("gateway")
    if isinstance(g, dict):
        t = display_scalar(g.get("connectionState"))
        if t and t != "—":
            return f"Gateway {t}"
    return "—"


def vehicle_list_activity(row) -> str:
    """active | inactive | unknown — for list badge (payload heuristics)."""
    p = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    for key in ("engineState", "vehicleEngineState", "motionStatus"):
        v = p.get(key)
        if not isinstance(v, str) or not v.strip():
            continue
        sl = v.strip().lower()
        if sl in ("off", "stopped", "parked", "sleep", "unknown"):
            return "inactive"
        if sl in ("on", "idle", "moving", "running", "roaming", "trip"):
            return "active"
    g = p.get("gateway")
    if isinstance(g, dict):
        cs = g.get("connectionState")
        if isinstance(cs, str) and cs.strip():
            sl = cs.strip().lower()
            if sl in ("disconnected", "offline"):
                return "inactive"
            if sl in ("connected", "online"):
                return "active"
    return "unknown"


def vehicle_detail_sections(vehicle) -> dict:
    """Structured display data for vehicle detail (no raw JSON)."""
    p = vehicle.raw_payload
    if not isinstance(p, dict):
        p = {}

    main_rows = []
    main_keys = {k for k, _ in VEHICLE_DETAIL_FIELD_LABELS}
    for key, label in VEHICLE_DETAIL_FIELD_LABELS:
        if key not in p:
            continue
        val = p.get(key)
        if key == "name" and isinstance(val, str):
            val = val.strip()
        text = display_scalar(val)
        if text is not None:
            main_rows.append((label, text))

    gateway_rows = []
    g = p.get("gateway")
    if isinstance(g, dict):
        for gkey, gval in sorted(g.items()):
            gt = display_scalar(gval)
            if gt is not None:
                gateway_rows.append((gkey.replace("_", " ").title(), gt))

    driver_rows = []
    d = p.get("staticAssignedDriver")
    if isinstance(d, dict):
        if "name" in d:
            driver_rows.append(("Name", display_scalar(d.get("name"))))
        if "id" in d:
            driver_rows.append(("Driver ID", display_scalar(d.get("id"))))

    tags = p.get("tags") if isinstance(p.get("tags"), list) else []

    extra_rows = []
    for key in sorted(p.keys()):
        if key in main_keys or key in VEHICLE_DETAIL_NESTED_SKIP or key in VEHICLE_DETAIL_EXTRA_SKIP:
            continue
        val = p.get(key)
        text = display_scalar(val)
        if text is not None:
            extra_rows.append((key, text))

    ext_rows = []
    ext = vehicle.external_ids
    if isinstance(ext, dict):
        for k, v in sorted(ext.items()):
            vt = display_scalar(v)
            if vt is not None:
                ext_rows.append((k, vt))

    return {
        "main_rows": main_rows,
        "gateway_rows": gateway_rows,
        "driver_rows": driver_rows,
        "tags": tags,
        "extra_rows": extra_rows,
        "external_id_rows": ext_rows,
    }
