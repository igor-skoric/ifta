from django.contrib import admin

from .models import SamsaraDriver, SamsaraSyncRun, SamsaraTrip, SamsaraVehicle


@admin.register(SamsaraVehicle)
class SamsaraVehicleAdmin(admin.ModelAdmin):
    list_display = ("samsara_id", "name", "last_synced_at")
    search_fields = ("samsara_id", "name")


@admin.register(SamsaraDriver)
class SamsaraDriverAdmin(admin.ModelAdmin):
    list_display = ("samsara_id", "name", "username", "last_synced_at")
    search_fields = ("samsara_id", "name", "username")


@admin.register(SamsaraSyncRun)
class SamsaraSyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "resource",
        "success",
        "fetched_count",
        "upserted_count",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("resource", "success")


@admin.register(SamsaraTrip)
class SamsaraTripAdmin(admin.ModelAdmin):
    list_display = ("samsara_id", "vehicle_samsara_id", "driver_samsara_id", "start_time", "distance_meters")
    search_fields = ("samsara_id", "vehicle_samsara_id", "driver_samsara_id")
