# app/admin.py
from django.contrib import admin

from dispatch.models import DispatchDriver

from .models import Department, OfficeDirectoryEmployee, OfficeEquipmentItem, OfficeEquipmentItemNote


class DispatchDriverInline(admin.TabularInline):
    model = DispatchDriver
    fk_name = "dispatcher"
    extra = 0
    fields = ("first_name", "last_name", "is_active", "sort_order")
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")
    list_editable = ("sort_order", "is_active")


@admin.register(OfficeDirectoryEmployee)
class OfficeDirectoryEmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "first_name",
        "last_name",
        "department",
        "position",
        "location",
        "login_type",
        "is_dispatcher",
        "is_active",
    )
    search_fields = (
        "employee_id",
        "first_name",
        "last_name",
        "work_email",
        "private_email",
        "work_phone",
        "private_phone",
        "position",
        "location",
    )
    list_filter = ("department", "login_type", "is_active", "is_dispatcher")
    ordering = ("last_name", "first_name")
    inlines = [DispatchDriverInline]


@admin.register(OfficeEquipmentItem)
class OfficeEquipmentItemAdmin(admin.ModelAdmin):
    list_display = ("asset_id", "equipment_type", "brand_model", "assigned_employee")
    search_fields = ("asset_id", "brand_model", "serial_number")
    list_filter = ("equipment_type",)
    autocomplete_fields = ("assigned_employee",)


@admin.register(OfficeEquipmentItemNote)
class OfficeEquipmentItemNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "created_at", "created_by", "body_preview")
    list_filter = ("created_at",)
    search_fields = ("body", "item__asset_id")
    autocomplete_fields = ("item",)
    readonly_fields = ("created_at",)

    @admin.display(description="Preview")
    def body_preview(self, obj):
        t = (obj.body or "").replace("\n", " ")
        return (t[:80] + "…") if len(t) > 80 else t or "—"
