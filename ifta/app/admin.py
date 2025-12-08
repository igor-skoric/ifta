from django.contrib import admin
from .models import State, StateTaxRate, VehicleRecord

admin.site.register(State)
admin.site.register(StateTaxRate)


@admin.register(VehicleRecord)
class VehicleRecordAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'jurisdiction', 'total_miles', 'fuel_qty', 'file_name')
    search_fields = ('vehicle', 'jurisdiction')
    list_filter = ('jurisdiction', 'file_name')  # <- dodato
    ordering = ('file_name', 'vehicle')

