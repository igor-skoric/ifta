"""Link dispatch equipment units to synced Samsara vehicles (name = unit number)."""

from __future__ import annotations

from urllib.parse import quote

from django.urls import reverse


def _osm_embed_url(lat: float, lng: float, *, delta: float = 0.02) -> str:
    """OpenStreetMap embed (no Leaflet — avoids Tailwind img max-width conflicts)."""
    west, south = lng - delta, lat - delta
    east, north = lng + delta, lat + delta
    return (
        "https://www.openstreetmap.org/export/embed.html"
        f"?bbox={west}%2C{south}%2C{east}%2C{north}"
        f"&layer=mapnik&marker={lat}%2C{lng}"
    )


def samsara_vehicle_for_unit(unit_number: str):
    """Return synced SamsaraVehicle whose name matches dispatch unit number."""
    unit = (unit_number or "").strip()
    if not unit:
        return None
    from samsara.models import SamsaraVehicle

    return SamsaraVehicle.objects.filter(name__iexact=unit).first()


def _samsara_db_context(
    truck, vehicle, *, current_assignment=None, include_payload_sections: bool = False
) -> dict:
    """Database-only context for truck Samsara tab (no HTTP calls to Samsara)."""
    unit = (truck.unit_number or "").strip()
    search_url = reverse("samsara:vehicle_list")
    if unit:
        search_url = f"{search_url}?q={quote(unit)}"

    trailers = list(truck.trailers) if hasattr(truck, "trailers") else []
    driver = truck.driver if hasattr(truck, "driver") else None

    base = {
        "samsara_vehicle": vehicle,
        "samsara_vehicle_detail_url": "",
        "samsara_vehicle_trips_url": "",
        "samsara_trips_count": 0,
        "samsara_vehicle_list_url": search_url,
        "samsara_vehicle_status_display": "",
        "samsara_last_trip": None,
        "main_rows": [],
        "gateway_rows": [],
        "driver_rows": [],
        "tags": [],
        "extra_rows": [],
        "external_id_rows": [],
        "samsara_dispatch_trailers": trailers,
        "samsara_dispatch_driver": driver,
        "samsara_dispatch_assigned_since": (
            current_assignment.started_at if current_assignment else None
        ),
        "samsara_gps": None,
        "samsara_gps_error": "",
        "samsara_gps_embed_url": "",
        "samsara_gps_show_map": False,
        "samsara_live_stats": None,
        "samsara_live_stats_error": "",
    }

    if vehicle is None:
        return base

    from samsara.models import SamsaraTrip
    from samsara.vehicle_display import vehicle_detail_sections, vehicle_status_display

    trips_count = SamsaraTrip.objects.filter(vehicle_samsara_id=vehicle.samsara_id).count()
    last_trip = (
        SamsaraTrip.objects.filter(vehicle_samsara_id=vehicle.samsara_id)
        .order_by("-start_time", "-samsara_id")
        .first()
    )

    base.update(
        {
            "samsara_vehicle_detail_url": reverse(
                "samsara:vehicle_detail", args=[vehicle.samsara_id]
            ),
            "samsara_vehicle_trips_url": reverse(
                "samsara:vehicle_trip_list", args=[vehicle.samsara_id]
            ),
            "samsara_trips_count": trips_count,
            "samsara_vehicle_status_display": vehicle_status_display(vehicle),
            "samsara_last_trip": last_trip,
        }
    )
    if include_payload_sections:
        base.update(vehicle_detail_sections(vehicle))
    return base


def samsara_context_for_truck(
    truck, *, current_assignment=None, refresh_live: bool = False
) -> dict:
    """Full Samsara tab context: DB + live API (GPS, fuel, engine, faults)."""
    unit = (truck.unit_number or "").strip()
    vehicle = samsara_vehicle_for_unit(unit)
    ctx = _samsara_db_context(
        truck, vehicle, current_assignment=current_assignment, include_payload_sections=True
    )
    if vehicle is None:
        return ctx

    from samsara.vehicle_live_stats import fetch_vehicle_live_stats_safe
    from samsara.vehicle_location import fetch_vehicle_gps_safe

    gps, gps_err = fetch_vehicle_gps_safe(
        vehicle.samsara_id, use_cache=not refresh_live
    )
    live_stats, live_err = fetch_vehicle_live_stats_safe(vehicle.samsara_id)

    embed_url = ""
    show_map = False
    if gps:
        show_map = True
        embed_url = _osm_embed_url(gps.latitude, gps.longitude)

    ctx.update(
        {
            "samsara_gps": gps,
            "samsara_gps_error": gps_err or "",
            "samsara_gps_embed_url": embed_url,
            "samsara_gps_show_map": show_map,
            "samsara_live_stats": live_stats,
            "samsara_live_stats_error": live_err or "",
        }
    )
    return ctx
