from django.contrib import admin

from .models import EmailVerificationToken, Role, RolePermission, UserProfile, UserRole


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_system")
    search_fields = ("name", "slug")
    list_filter = ("is_system",)
    filter_horizontal = ("allowed_departments",)
    inlines = (RolePermissionInline,)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "email_verified", "can_login", "ui_theme")
    search_fields = ("user__username", "user__email")
    list_filter = ("email_verified", "can_login", "department", "ui_theme")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_by", "created_at")
    search_fields = ("user__username", "user__email", "role__name")
    list_filter = ("role",)


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "expires_at", "consumed_at", "created_at")
    search_fields = ("user__username", "user__email")
    list_filter = ("expires_at", "consumed_at")
