from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from .models import UserRole


def get_user_permission_codes(user):
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {"*"}
    rows = UserRole.objects.filter(user=user).values_list("role__permissions__code", flat=True)
    return {code for code in rows if code}


def has_permission(user, code):
    permissions = get_user_permission_codes(user)
    return "*" in permissions or code in permissions


def is_user_department_allowed(user, role):
    if user.is_superuser:
        return True
    allowed_departments = role.allowed_departments.all()
    if not allowed_departments.exists():
        return True
    if not hasattr(user, "profile") or not user.profile.department_id:
        return False
    return allowed_departments.filter(id=user.profile.department_id).exists()


def has_permission_for_user_context(user, code):
    if user.is_superuser:
        return True
    if not user.is_authenticated:
        return False
    assignments = UserRole.objects.filter(user=user).select_related("role")
    for assignment in assignments:
        if assignment.role.permissions.filter(code=code).exists() and is_user_department_allowed(user, assignment.role):
            return True
    return False

