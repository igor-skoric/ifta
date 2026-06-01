from django.conf import settings
from django.db.models import Count

from core.timezone_utils import app_now


def _breadcrumb_label(segment):
    known_labels = {
        "accounts": "Accounts",
        "settings": "Settings",
        "ifta": "IFTA",
        "statistics": "Statistics",
        "office": "Office",
        "leave": "Leave",
        "samsara": "Samsara",
        "dispatch": "Dispatch",
        "statistics": "Statistics",
        "drivers": "Drivers",
        "trailers": "Trailers",
        "trucks": "Trucks",
        "trips": "Trips",
        "new": "New",
        "map": "Map",
        "people": "People",
        "inventory": "Inventory",
        "new": "New",
        "edit": "Edit",
        "balances": "Vacation days",
        "allowance": "Allowance",
    }
    if segment in known_labels:
        return known_labels[segment]
    return segment.replace("-", " ").replace("_", " ").title()


def universal_settings(request):
    statistics_api_base_url = getattr(settings, "STATISTICS_API_BASE_URL", "/api/statistic")
    office_people_by_department = []
    office_people_by_login_type = []
    office_inventory_by_state = []

    try:
        from office.models import OfficeDirectoryEmployee, OfficeEquipmentItem

        office_people_by_department = list(
            OfficeDirectoryEmployee.objects.filter(is_active=True)
            .exclude(department__isnull=True)
            .values("department__name")
            .annotate(count=Count("id"))
            .order_by("department__name")
        )
        office_people_by_login_type = list(
            OfficeDirectoryEmployee.objects.values("login_type")
            .annotate(count=Count("id"))
            .order_by("login_type")
        )
        office_inventory_by_state = list(
            OfficeEquipmentItem.objects.values("state")
            .annotate(count=Count("id"))
            .order_by("state")
        )
    except Exception:
        # Avoid breaking pages during early migrations or missing tables.
        pass

    app_ui_theme = "dark"
    if getattr(request, "user", None) and request.user.is_authenticated:
        try:
            app_ui_theme = request.user.profile.ui_theme
        except Exception:
            app_ui_theme = "dark"

    path = (request.path or "/").strip("/")
    parts = [part for part in path.split("/") if part]
    breadcrumbs = [{"label": "Home", "url": "/"}]
    current_path = ""
    for part in parts:
        current_path = f"{current_path}/{part}"
        breadcrumbs.append({"label": _breadcrumb_label(part), "url": current_path + "/"})

    return {
        "topbar_notification_count": 0,
        "statistics_api_base_url": statistics_api_base_url.rstrip("/"),
        "domain_apps": getattr(settings, "DOMAIN_APPS", ("ifta", "statistics", "office")),
        "office_people_by_department": office_people_by_department,
        "office_people_by_login_type": office_people_by_login_type,
        "office_inventory_by_state": office_inventory_by_state,
        "breadcrumbs": breadcrumbs,
        "app_ui_theme": app_ui_theme,
        "app_now": app_now(),
        "app_timezone_tz": settings.TIME_ZONE,
    }
