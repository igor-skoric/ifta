from django.contrib import admin
from .models import WeeklyDriverData, WeeklyDayData, ActiveTrucksFinalGross, SheetConfig

admin.site.register(WeeklyDriverData)
admin.site.register(WeeklyDayData)
admin.site.register(ActiveTrucksFinalGross)
admin.site.register(SheetConfig)