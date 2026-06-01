from django.contrib import admin

from .models import WeeklyDayData, SheetConfig, DispatcherSheetRow


@admin.register(WeeklyDayData)
class WeeklyDayDataAdmin(admin.ModelAdmin):
    list_display = ("year", "iso_week", "day", "gross", "cut", "miles", "rate_per_mile", "updated_at")
    list_filter = ("year", "iso_week")
    ordering = ("-year", "-iso_week", "day")


admin.site.register(SheetConfig)


@admin.register(DispatcherSheetRow)
class DispatcherSheetRowAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "iso_week",
        "dispatcher",
        "gross",
        "cut",
        "miles",
        "rpm",
        "gpu",
        "drpm",
        "imported_at",
        "updated_at",
    )
    search_fields = ("dispatcher",)
    list_filter = ("year", "iso_week")
    ordering = ("-year", "-iso_week", "-imported_at", "dispatcher")
    list_per_page = 100
