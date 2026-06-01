from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.security import can_read_statistics


class StatisticsReadPermission(BasePermission):
    """GET statistics APIs: authenticated statistics.view OR TV allowlist/token."""

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        return can_read_statistics(request)


class StatisticsAnalyticsPermission(BasePermission):
    """Historical weekly analytics — never public TV; requires statistics.view."""

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from accounts.services import has_permission_for_user_context

        return has_permission_for_user_context(user, "statistics.view")
