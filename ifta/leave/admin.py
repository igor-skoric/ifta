from django.contrib import admin

from .models import LeaveAllowance, LeaveEntry


@admin.register(LeaveEntry)
class LeaveEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "updated_at")
    list_filter = ("leave_type", "start_date", "end_date")
    search_fields = (
        "employee__employee_id",
        "employee__first_name",
        "employee__last_name",
        "note",
    )
    autocomplete_fields = ("employee",)


@admin.register(LeaveAllowance)
class LeaveAllowanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "year", "granted_days", "updated_at")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")
    list_filter = ("year",)
    autocomplete_fields = ("employee",)

