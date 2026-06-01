import time

import requests
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone


class SamsaraApiError(Exception):
    pass


class SamsaraClient:
    def __init__(self):
        self.base_url = getattr(settings, "SAMSARA_API_BASE_URL", "https://api.samsara.com").rstrip("/")
        self.token = getattr(settings, "SAMSARA_API_TOKEN", "").strip()
        self.timeout = int(getattr(settings, "SAMSARA_API_TIMEOUT_SECONDS", 20))
        if not self.token:
            raise SamsaraApiError("SAMSARA_API_TOKEN is missing. Add it to environment variables.")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        max_retries = max(1, int(getattr(settings, "SAMSARA_API_RETRY_MAX", 4)))
        last_response = None
        for attempt in range(max_retries):
            last_response = self._session.get(url, params=params or {}, timeout=self.timeout)
            if last_response.status_code < 500:
                break
            if attempt < max_retries - 1:
                time.sleep(min(8.0, 0.5 * (2**attempt)))
        response = last_response
        if response.status_code >= 400:
            raise SamsaraApiError(f"Samsara API error {response.status_code}: {response.text[:500]}")
        try:
            return response.json()
        except ValueError as exc:
            raise SamsaraApiError("Samsara API returned invalid JSON.") from exc

    def list_vehicles(self):
        # Endpoint path is configurable in settings to allow easier API version changes.
        path = getattr(settings, "SAMSARA_VEHICLES_ENDPOINT", "/fleet/vehicles")
        payload = self._get(path)
        return payload.get("data", [])

    def list_drivers(self):
        path = getattr(settings, "SAMSARA_DRIVERS_ENDPOINT", "/fleet/drivers")
        payload = self._get(path)
        return payload.get("data", [])

    @staticmethod
    def _ms_to_iso(ms, ongoing_sentinel=9223372036854775807):
        if ms is None or ms >= ongoing_sentinel - 1:
            return None
        return (
            datetime.fromtimestamp(ms / 1000.0, tz=dt_timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

    def _normalize_legacy_trip(self, item, vehicle_id_str):
        """Legacy /v1/fleet/trips vraća startMs/endMs; view očekuje id, startTime, endTime, vehicleId."""
        start_ms = item.get("startMs")
        end_ms = item.get("endMs")
        if start_ms is None:
            return None
        start_iso = self._ms_to_iso(start_ms) or ""
        end_iso = self._ms_to_iso(end_ms) or ""
        driver_raw = item.get("driverId")
        driver_id = "" if driver_raw is None else str(driver_raw)
        trip_id = f"{vehicle_id_str}_{start_ms}_{end_ms}"
        merged = {
            **item,
            "id": trip_id,
            "vehicleId": vehicle_id_str,
            "startTime": start_iso,
            "endTime": end_iso,
        }
        if driver_id:
            merged["driverId"] = driver_id
        return merged

    def get_vehicle_locations_feed(self, vehicle_ids=None, after=None):
        """
        Latest GPS per vehicle from /fleet/vehicles/locations/feed.
        vehicle_ids: optional list of Samsara vehicle id strings.
        """
        path = getattr(
            settings, "SAMSARA_LOCATIONS_FEED_ENDPOINT", "/fleet/vehicles/locations/feed"
        )
        params = {}
        if after:
            params["after"] = after
        if vehicle_ids:
            ids = [str(v).strip() for v in vehicle_ids if str(v).strip()]
            if ids:
                params["vehicleIds"] = ",".join(ids)
        return self._get(path, params=params or None)

    def get_vehicle_stats(self, vehicle_ids, types):
        """Point-in-time vehicle stats snapshot (max 3 types per Samsara request)."""
        path = getattr(settings, "SAMSARA_VEHICLE_STATS_ENDPOINT", "/fleet/vehicles/stats")
        ids = [str(v).strip() for v in vehicle_ids if str(v).strip()]
        if not ids:
            return {"data": []}
        type_list = [str(t).strip() for t in types if str(t).strip()]
        if not type_list:
            return {"data": []}
        if len(type_list) > 3:
            raise ValueError("Samsara allows at most 3 stat types per request.")
        return self._get(
            path,
            params={"vehicleIds": ",".join(ids), "types": ",".join(type_list)},
        )

    def get_vehicle_stats_gps(self, vehicle_ids):
        """Point-in-time GPS via /fleet/vehicles/stats?types=gps."""
        return self.get_vehicle_stats(vehicle_ids, ["gps"])

    def list_trips(self, start_ms=None, end_ms=None):
        """
        Samsara trips su na legacy GET /v1/fleet/trips po jednom vozilu (vehicleId, startMs, endMs).
        Novi /fleet/trips ne postoji — zato je čest 404 ako se zove pogrešna putanja.

        Ako start_ms/end_ms nisu prosleđeni, koristi se prozor SAMSARA_TRIPS_DAYS_BACK (puna istorija
        u tom opsegu) — zgodno za skripte; sync_trips uvek prosleđuje eksplicitan prozor.
        """
        path = getattr(settings, "SAMSARA_TRIPS_ENDPOINT", "/v1/fleet/trips")
        if end_ms is None:
            end_ms = int(timezone.now().timestamp() * 1000)
        if start_ms is None:
            days_back = int(getattr(settings, "SAMSARA_TRIPS_DAYS_BACK", 14))
            start_ms = end_ms - int(timedelta(days=days_back).total_seconds() * 1000)

        vehicles = self.list_vehicles()
        trip_delay = float(getattr(settings, "SAMSARA_TRIPS_INTER_REQUEST_DELAY_SECONDS", 0.25))
        out = []
        for i, v in enumerate(vehicles):
            vid = v.get("id")
            if vid is None or vid == "":
                continue
            if i > 0 and trip_delay > 0:
                time.sleep(trip_delay)
            vid_param = int(vid) if isinstance(vid, str) and str(vid).isdigit() else vid
            params = {"vehicleId": vid_param, "startMs": start_ms, "endMs": end_ms}
            payload = self._get(path, params=params)
            trips = payload.get("trips")
            if trips is None:
                trips = payload.get("data") or []
            vehicle_id_str = str(vid)
            for t in trips:
                normalized = self._normalize_legacy_trip(t, vehicle_id_str)
                if normalized:
                    out.append(normalized)
        return out
