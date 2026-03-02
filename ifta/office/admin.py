# app/admin.py
from django.contrib import admin
from django.utils import timezone

from .models import (
    Seat,
    Employee,
    Asset,
    AssetAssignment,
    SeatAssignment,
)


# -------- Inlines --------

class SeatAssignmentInline(admin.TabularInline):
    model = SeatAssignment
    extra = 0
    autocomplete_fields = ("seat", "employee")
    fields = ("seat", "start_at", "end_at", "note")
    ordering = ("-start_at",)
    show_change_link = True


class AssetAssignmentInline(admin.TabularInline):
    model = AssetAssignment
    extra = 0
    autocomplete_fields = ("asset", "employee")
    fields = ("asset", "start_at", "end_at", "assigned_by", "note")
    ordering = ("-start_at",)
    show_change_link = True


# -------- Seat --------

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("svg_id", "label", "dept", "zone", "seat_no", "is_active")
    list_display_links = ("svg_id", "label")
    list_filter = ("is_active", "dept", "zone")
    search_fields = ("svg_id", "label", "dept", "zone", "seat_no")
    ordering = ("dept", "zone", "seat_no", "svg_id")
    list_per_page = 50
    list_editable = ("dept", "zone", "seat_no", "is_active")

    # da možeš iz Seat-a da vidiš zaduženja
    inlines = (SeatAssignmentInline,)


# -------- Employee --------

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("alias", "name", "email", "phone", "company_name", "is_active")
    list_display_links = ("alias", "name")
    list_filter = ("is_active", "company_name")
    search_fields = ("alias", "name", "email", "phone", "company_name", "company_email", "company_phone")
    ordering = ("alias",)
    list_per_page = 50
    list_editable = ("is_active",)

    fieldsets = (
        ("Basic", {"fields": ("alias", "name", "is_active")}),
        ("Contact", {"fields": ("email", "phone")}),
        ("Company", {"fields": ("company_name", "company_email", "company_phone")}),
    )

    inlines = (SeatAssignmentInline, AssetAssignmentInline)


# -------- Asset --------

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_type", "brand", "model", "serial_number", "inventory_tag", "status", "created_at")
    list_display_links = ("asset_type", "brand", "model")
    list_filter = ("asset_type", "status", "created_at")
    search_fields = ("brand", "model", "serial_number", "inventory_tag", "notes")
    ordering = ("-created_at",)
    list_per_page = 50
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Asset", {"fields": ("asset_type", "status")}),
        ("Identification", {"fields": ("brand", "model", "serial_number", "inventory_tag")}),
        ("Notes", {"fields": ("notes",)}),
        ("Meta", {"fields": ("created_at",)}),
    )

    # da u Asset-u vidiš istoriju zaduženja
    inlines = (AssetAssignmentInline,)


# -------- AssetAssignment --------

@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ("asset", "employee", "start_at", "end_at", "is_active_assignment", "assigned_by")
    list_filter = ("end_at", "start_at", "asset__asset_type", "asset__status")
    search_fields = (
        "employee__alias", "employee__name", "employee__email",
        "asset__brand", "asset__model", "asset__serial_number", "asset__inventory_tag",
        "note", "assigned_by",
    )
    autocomplete_fields = ("asset", "employee")
    date_hierarchy = "start_at"
    ordering = ("-start_at",)
    list_per_page = 50

    actions = ("close_assignment_now",)

    @admin.display(boolean=True, description="Active")
    def is_active_assignment(self, obj: AssetAssignment) -> bool:
        return obj.end_at is None

    @admin.action(description="Close selected assignments (set end_at=now)")
    def close_assignment_now(self, request, queryset):
        queryset.filter(end_at__isnull=True).update(end_at=timezone.now())


# -------- SeatAssignment --------

@admin.register(SeatAssignment)
class SeatAssignmentAdmin(admin.ModelAdmin):
    list_display = ("seat", "employee", "start_at", "end_at", "is_active_assignment")
    list_filter = ("end_at", "start_at", "seat__dept", "seat__zone")
    search_fields = (
        "seat__svg_id", "seat__label", "seat__dept", "seat__zone", "seat__seat_no",
        "employee__alias", "employee__name", "employee__email",
        "note",
    )
    autocomplete_fields = ("seat", "employee")
    date_hierarchy = "start_at"
    ordering = ("-start_at",)
    list_per_page = 50

    actions = ("close_assignment_now",)

    @admin.display(boolean=True, description="Active")
    def is_active_assignment(self, obj: SeatAssignment) -> bool:
        return obj.end_at is None

    @admin.action(description="Release seats (set end_at=now)")
    def close_assignment_now(self, request, queryset):
        queryset.filter(end_at__isnull=True).update(end_at=timezone.now())
