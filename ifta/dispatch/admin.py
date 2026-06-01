from django.contrib import admin



from .models import (

    DispatchAssignment,

    DispatchDriver,

    DispatchLoad,

    DispatchLoadComment,

    DispatchLoadStatusHistory,

    DispatchTrailer,

    DispatchTruck,

    DriverUnavailability,

)





class DispatchLoadStatusHistoryInline(admin.TabularInline):

    model = DispatchLoadStatusHistory

    extra = 0

    can_delete = False

    max_num = 0

    fields = ("changed_at", "from_status", "to_status", "changed_by", "source")

    readonly_fields = ("changed_at", "from_status", "to_status", "changed_by", "source")

    ordering = ("-changed_at", "-pk")



    def has_add_permission(self, request, obj=None):

        return False





class DispatchLoadCommentInline(admin.TabularInline):

    model = DispatchLoadComment

    extra = 0

    fields = ("body", "created_by", "created_at")

    readonly_fields = ("created_at",)

    ordering = ("-created_at",)





@admin.register(DispatchLoad)

class DispatchLoadAdmin(admin.ModelAdmin):

    list_display = (

        "broker_or_customer",

        "planner_date",

        "driver",

        "status",

        "rc_status",

        "pod_status",

        "pickup_city",

        "delivery_city",

        "pickup_datetime",

        "delivery_datetime",

        "loaded_miles",

        "linehaul_amount",

    )

    list_filter = ("status", "rc_status", "pod_status", "planner_date")

    search_fields = (

        "broker_or_customer",

        "pickup_city",

        "delivery_city",

        "bol_number",

        "po_number",

        "notes",

    )

    autocomplete_fields = ("driver",)

    inlines = [DispatchLoadCommentInline, DispatchLoadStatusHistoryInline]





class DispatchDriverAssignmentInline(admin.TabularInline):

    model = DispatchAssignment

    fk_name = "driver"

    extra = 0

    fields = ("truck", "trailer", "started_at", "ended_at", "notes")

    readonly_fields = ("started_at",)

    ordering = ("-started_at",)

    show_change_link = True





class DriverUnavailabilityInline(admin.TabularInline):

    model = DriverUnavailability

    extra = 0

    fields = ("reason", "start_date", "end_date", "note")

    ordering = ("-start_date",)





class DispatchTruckAssignmentInline(admin.TabularInline):

    model = DispatchAssignment

    fk_name = "truck"

    extra = 0

    fields = ("driver", "trailer", "started_at", "ended_at", "notes")

    readonly_fields = ("started_at",)

    ordering = ("-started_at",)

    show_change_link = True





class DispatchTrailerAssignmentInline(admin.TabularInline):

    model = DispatchAssignment

    fk_name = "trailer"

    extra = 0

    fields = ("driver", "truck", "started_at", "ended_at", "notes")

    readonly_fields = ("started_at",)

    ordering = ("-started_at",)

    show_change_link = True





@admin.register(DispatchDriver)

class DispatchDriverAdmin(admin.ModelAdmin):

    list_display = (

        "first_name",

        "last_name",

        "legacy_driver_id",

        "fleet_company",

        "hire_date",

        "driveroo_status",

        "dispatcher",

        "is_active",

        "sort_order",

    )

    list_filter = ("is_active", "dispatcher", "driveroo_status", "fleet_company", "comp_oo_local_legal")

    search_fields = (

        "first_name",

        "last_name",

        "legacy_driver_id",

        "phone",

        "email",

        "notes",

        "dispatcher__employee_id",

        "dispatcher__first_name",

        "dispatcher__last_name",

    )

    ordering = ("dispatcher", "sort_order", "last_name")

    inlines = [DriverUnavailabilityInline, DispatchDriverAssignmentInline]

    autocomplete_fields = ("dispatcher",)





@admin.register(DispatchTruck)

class DispatchTruckAdmin(admin.ModelAdmin):

    list_display = ("unit_number", "is_active", "created_at")

    list_filter = ("is_active",)

    search_fields = ("unit_number", "notes")

    inlines = [DispatchTruckAssignmentInline]





@admin.register(DispatchTrailer)

class DispatchTrailerAdmin(admin.ModelAdmin):

    list_display = ("unit_number", "is_active", "created_at")

    list_filter = ("is_active",)

    search_fields = ("unit_number", "notes")

    inlines = [DispatchTrailerAssignmentInline]





@admin.register(DispatchAssignment)

class DispatchAssignmentAdmin(admin.ModelAdmin):

    list_display = ("driver", "truck", "trailer", "started_at", "ended_at")

    list_filter = ("ended_at",)

    search_fields = (

        "driver__first_name",

        "driver__last_name",

        "truck__unit_number",

        "trailer__unit_number",

        "notes",

    )

    autocomplete_fields = ("driver", "truck", "trailer")

    ordering = ("-started_at",)

