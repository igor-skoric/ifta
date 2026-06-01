from django.db import models


class SamsaraVehicle(models.Model):
    samsara_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    external_ids = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "samsara_id"]

    def __str__(self):
        return self.name or self.samsara_id


class SamsaraDriver(models.Model):
    samsara_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    username = models.CharField(max_length=255, blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "username", "samsara_id"]

    def __str__(self):
        return self.name or self.username or self.samsara_id


class SamsaraTrip(models.Model):
    samsara_id = models.CharField(max_length=64, unique=True)
    vehicle_samsara_id = models.CharField(max_length=64, blank=True, default="")
    driver_samsara_id = models.CharField(max_length=64, blank=True, default="")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    distance_meters = models.FloatField(default=0)
    raw_payload = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_time", "samsara_id"]
        indexes = [
            models.Index(fields=["driver_samsara_id", "start_time"]),
            models.Index(fields=["vehicle_samsara_id", "start_time"]),
        ]

    def __str__(self):
        return self.samsara_id

    @property
    def distance_km(self):
        return (self.distance_meters or 0) / 1000.0


class SamsaraTripsSyncState(models.Model):
    """
    Singleton row (pk=1): end timestamp of the last successful trips sync window.
    Used for incremental pulls (startMs = last end minus overlap).
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    last_query_end_ms = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="End of last successful trips API window (Unix ms).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Samsara trips sync state"

    def __str__(self):
        return f"SamsaraTripsSyncState(end_ms={self.last_query_end_ms})"


class SamsaraSyncRun(models.Model):
    RESOURCE_CHOICES = [
        ("vehicles", "Vehicles"),
        ("drivers", "Drivers"),
        ("trips", "Trips"),
    ]
    resource = models.CharField(max_length=32, choices=RESOURCE_CHOICES)
    success = models.BooleanField(default=False)
    fetched_count = models.PositiveIntegerField(default=0)
    upserted_count = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def duration_display(self):
        if self.duration_seconds is None:
            return "—"
        d = float(self.duration_seconds)
        if d < 60:
            return f"{d:.1f}s"
        m = int(d // 60)
        s = d - m * 60
        return f"{m}m {s:.1f}s"
