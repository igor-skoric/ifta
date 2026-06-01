from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import permission_required
from accounts.services import has_permission_for_user_context
from office.models import OfficeDirectoryEmployee

from .forms import (
    DispatchDriverForm,
    DriverUnavailabilityForm,
    DispatchLoadForm,
    DispatchTrailerForm,
    DispatchTruckForm,
)
from .driver_availability import entries_for_drivers_between, unavailability_by_cell
from .load_validation import collect_load_schedule_dates, validate_driver_assignment_for_load
from .load_comments import serialize_load_comment
from .load_docs_status import PODStatus, RCStatus
from .load_status import LoadStatus, workflow_steps_for_load
from .status_history import (
    SOURCE_LOAD_CREATE,
    SOURCE_LOAD_DETAIL,
    SOURCE_LOAD_FORM,
    SOURCE_PLANNER,
    apply_load_status_change,
    record_load_status_change,
)
from .assignments import (
    assigned_trailer_ids,
    set_driver_equipment,
    set_trailer_equipment,
    set_truck_equipment,
    assigned_truck_ids,
    assignment_history_for_driver,
    assignment_history_for_trailer,
    assignment_history_for_truck,
    attach_current_driver_to_trailers,
    attach_current_driver_to_trucks,
    attach_current_equipment_to_drivers,
    current_assignments,
    current_assignments_for_driver,
    driver_search_q,
    load_search_q,
    trailer_search_q,
    truck_search_q,
)
from .driver_import import import_drivers_from_rows, parse_csv_file, sample_csv_bytes
from .samsara_links import samsara_context_for_truck
from .planner_cells import planner_days_for_load
from .dispatcher_ranking import (
    PERIOD_CHOICES as RANKING_PERIOD_CHOICES,
    SORT_CHOICES,
    build_leaderboard_rows,
    loads_in_range as ranking_loads_in_range,
    parse_ranking_params,
    period_label as ranking_period_label,
    sort_leaderboard,
)
from .statistics import (
    PERIOD_CHOICES,
    build_dispatcher_rows,
    build_driver_rows,
    build_fleet_totals,
    dispatcher_choices,
    loads_in_range,
    parse_statistics_filters,
)
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

DISPATCH_ENTITY_MODAL_HEADER = "X-Dispatch-Entity-Modal"


def _is_dispatch_entity_modal(request) -> bool:
    return request.headers.get(DISPATCH_ENTITY_MODAL_HEADER) == "1"


def _dispatch_entity_form_success(request, redirect_url: str, message: str):
    messages.success(request, message)
    if _is_dispatch_entity_modal(request):
        return JsonResponse({"ok": True, "redirect": redirect_url})
    return redirect(redirect_url)


def _render_dispatch_entity_form(
    request, *, full_template: str, modal_template: str, ctx: dict
):
    is_modal = _is_dispatch_entity_modal(request)
    status = 422 if request.method == "POST" and is_modal else 200
    template = modal_template if is_modal else full_template
    return render(request, template, ctx, status=status)


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


DAY_HEADERS = [
    ("MON", "Monday"),
    ("TUE", "Tuesday"),
    ("WED", "Wednesday"),
    ("THU", "Thursday"),
    ("FRI", "Friday"),
    ("SAT", "Saturday"),
    ("SUN", "Sunday"),
]


def _serialize_load_for_dialog(ld: DispatchLoad) -> dict:
    dr = ld.driver
    dispatcher = dr.dispatcher if dr else None
    truck = dr.truck if dr else None
    trailers = [tr.unit_number for tr in dr.trailers.all()] if dr else []
    disp_name = ""
    if dispatcher:
        disp_name = f"{dispatcher.first_name} {dispatcher.last_name}".strip()
    pickup_place = ld.pickup_display()
    delivery_place = ld.delivery_display()
    linehaul_display = ""
    if ld.linehaul_amount is not None:
        linehaul_display = f"${ld.linehaul_amount:,.2f}"
    return {
        "id": ld.pk,
        "detail_url": reverse("dispatch:load_detail", args=[ld.pk]),
        "edit_url": reverse("dispatch:load_edit", args=[ld.pk]),
        "reference": ld.display_title(),
        "load_id": ld.load_id_display(),
        "lane_label": f"{pickup_place or '—'} → {delivery_place or '—'}",
        "status": ld.get_status_display(),
        "status_slug": ld.status,
        "rc_status": ld.get_rc_status_display(),
        "rc_status_slug": ld.rc_status,
        "pod_status": ld.get_pod_status_display(),
        "pod_status_slug": ld.pod_status,
        "notes": ld.notes or "",
        "dispatcher": disp_name,
        "driver_name": dr.display_name if dr else "",
        "truck": truck.unit_number if truck else "",
        "trailers": ", ".join(trailers),
        "pickup": pickup_place,
        "delivery": delivery_place,
        "pickup_window": (ld.pickup_window or "").strip(),
        "delivery_window": (ld.delivery_window or "").strip(),
        "pickup_datetime": ld.pickup_datetime.isoformat() if ld.pickup_datetime else "",
        "delivery_datetime": ld.delivery_datetime.isoformat() if ld.delivery_datetime else "",
        "loaded_miles": ld.loaded_miles,
        "linehaul": str(ld.linehaul_amount) if ld.linehaul_amount is not None else "",
        "linehaul_display": linehaul_display,
        "comment_count": getattr(ld, "comment_count", None) or ld.comments.count(),
        "comments_url": reverse("dispatch:load_comments", args=[ld.pk]),
        "comments_create_url": reverse("dispatch:load_comment_create", args=[ld.pk]),
    }


@permission_required("dispatch.view")
def planner(request):
    week_raw = (request.GET.get("week") or "").strip()
    today = date.today()
    if week_raw:
        try:
            parsed = date.fromisoformat(week_raw)
            monday = _monday_of_week(parsed)
        except ValueError:
            monday = _monday_of_week(today)
    else:
        monday = _monday_of_week(today)

    sunday = monday + timedelta(days=6)
    prev_week = (monday - timedelta(days=7)).isoformat()
    next_week = (monday + timedelta(days=7)).isoformat()

    driver_qs = (
        DispatchDriver.objects.filter(is_active=True)
        .select_related("dispatcher")
        .order_by("sort_order", "last_name", "first_name")
    )

    dispatchers = (
        OfficeDirectoryEmployee.objects.filter(is_active=True, is_dispatcher=True)
        .annotate(
            active_assigned_driver_count=Count(
                "dispatch_drivers",
                filter=Q(dispatch_drivers__is_active=True),
            )
        )
        .filter(active_assigned_driver_count__gt=0)
        .prefetch_related(
            Prefetch(
                "dispatch_drivers",
                queryset=driver_qs.order_by("sort_order", "last_name", "first_name"),
            )
        )
        .order_by("last_name", "first_name")
    )

    driver_ids = list(driver_qs.values_list("pk", flat=True))

    week_days = []
    for i, (short, full) in enumerate(DAY_HEADERS):
        d = monday + timedelta(days=i)
        week_days.append({"short": short, "full": full, "date": d, "is_today": d == today})

    loads_qs = DispatchLoad.objects.none()
    if driver_ids:
        loads_qs = (
            DispatchLoad.objects.filter(driver_id__in=driver_ids)
            .filter(
                Q(planner_date__gte=monday, planner_date__lte=sunday)
                | Q(
                    pickup_datetime__date__gte=monday,
                    pickup_datetime__date__lte=sunday,
                )
            )
            .select_related("driver", "driver__dispatcher")
            .annotate(comment_count=Count("comments"))
            .distinct()
        )
        load_drivers = {ld.driver for ld in loads_qs if ld.driver_id}
        attach_current_equipment_to_drivers(load_drivers)

    load_by_cell = defaultdict(list)
    dialog_by_cell = defaultdict(list)
    cell_load_ids: dict[str, set[int]] = defaultdict(set)
    for load in loads_qs:
        if not load.driver_id:
            continue
        driver_id = load.driver_id
        for grid_day in planner_days_for_load(load, monday=monday, sunday=sunday):
            key = f"{driver_id}_{grid_day.isoformat()}"
            if load.pk in cell_load_ids[key]:
                continue
            cell_load_ids[key].add(load.pk)
            load_by_cell[key].append(load)
            dialog_by_cell[key].append(_serialize_load_for_dialog(load))

    planner_drivers: list[DispatchDriver] = []
    for disp in dispatchers:
        planner_drivers.extend(list(disp.dispatch_drivers.all()))
    attach_current_equipment_to_drivers(planner_drivers)

    week_dates = [wd["date"] for wd in week_days]
    unavail_entries = entries_for_drivers_between(driver_ids, start=monday, end=sunday)
    unavail_by_cell = unavailability_by_cell(
        unavail_entries,
        driver_ids=driver_ids,
        days=week_dates,
    )

    return render(
        request,
        "dispatch/planner.html",
        {
            "hide_header_and_footer": False,
            "monday": monday,
            "sunday": sunday,
            "prev_week": prev_week,
            "next_week": next_week,
            "dispatchers": dispatchers,
            "week_days": week_days,
            "load_by_cell": dict(load_by_cell),
            "unavailability_by_cell": unavail_by_cell,
            "planner_loads_dialog": dict(dialog_by_cell),
            "load_status_choices": LoadStatus.choices,
            "load_status_choices_json": [
                {"value": value, "label": label} for value, label in LoadStatus.choices
            ],
            "load_status_url_sample": reverse("dispatch:load_status_update", kwargs={"pk": 0}),
            "load_comments_url_sample": reverse("dispatch:load_comments", kwargs={"pk": 0}),
            "can_manage_dispatch": has_permission_for_user_context(request.user, "dispatch.manage"),
        },
    )


@permission_required("dispatch.view")
def dispatch_statistics(request):
    view, date_from, date_to, dispatcher_filter, period = parse_statistics_filters(request)
    loads = loads_in_range(date_from, date_to)
    fleet = build_fleet_totals(loads)
    dispatcher_rows = build_dispatcher_rows(loads, dispatcher_filter=dispatcher_filter)
    driver_rows = build_driver_rows(loads, dispatcher_filter=dispatcher_filter)

    return render(
        request,
        "dispatch/statistics.html",
        {
            "hide_header_and_footer": False,
            "view_mode": view,
            "period": period,
            "period_choices": PERIOD_CHOICES,
            "date_from": date_from,
            "date_to": date_to,
            "filter_dispatcher": dispatcher_filter,
            "fleet": fleet,
            "dispatcher_rows": dispatcher_rows,
            "driver_rows": driver_rows,
            "dispatcher_choices": dispatcher_choices(),
        },
    )


@permission_required("dispatch.view")
def dispatcher_ranking(request):
    period, date_from, date_to, sort = parse_ranking_params(request)
    loads = ranking_loads_in_range(date_from, date_to)
    rows = build_leaderboard_rows(loads)
    rows = sort_leaderboard(rows, sort)
    podium = [r for r in rows if r.overall_rank and r.overall_rank <= 3 and r.load_count > 0]
    podium.sort(key=lambda r: r.overall_rank)
    period_links = [
        (key, label, f"?period={key}&sort={sort}") for key, label in RANKING_PERIOD_CHOICES
    ]
    sort_links = [
        (key, label, f"?period={period}&sort={key}") for key, label in SORT_CHOICES
    ]

    return render(
        request,
        "dispatch/dispatcher_ranking.html",
        {
            "hide_header_and_footer": False,
            "period": period,
            "period_label": ranking_period_label(period),
            "period_links": period_links,
            "sort": sort,
            "sort_links": sort_links,
            "date_from": date_from,
            "date_to": date_to,
            "rows": rows,
            "podium": podium,
        },
    )


def _search_q(request) -> str:
    return (request.GET.get("q") or "").strip()


DISPATCH_DRIVER_LIST_PER_PAGE = 25
DISPATCH_TRUCK_LIST_PER_PAGE = 25
DISPATCH_TRAILER_LIST_PER_PAGE = 25
DISPATCH_LOAD_LIST_PER_PAGE = 25


def _filter_querystring_without_page(request) -> str:
    qd = request.GET.copy()
    qd.pop("page", None)
    return qd.urlencode()


def _driver_list_filter_querystring(request) -> str:
    return _filter_querystring_without_page(request)


def _truck_trailer_list_filters(request) -> tuple[str, str]:
    """active: yes|no; assignment: assigned|unassigned (driver linked or not)."""
    active = (request.GET.get("active") or "").strip().lower()
    if active not in ("", "yes", "no"):
        active = ""
    assignment = (request.GET.get("assignment") or "").strip().lower()
    if assignment not in ("", "assigned", "unassigned"):
        assignment = ""
    return active, assignment


def _load_list_filters(request) -> tuple[str, str, str, str, str]:
    """GET filters: status, driver (pk), driver_assignment, planner_from/to (YYYY-MM-DD)."""
    from django.utils.dateparse import parse_date

    status = (request.GET.get("status") or "").strip()
    allowed_status = {value for value, _ in LoadStatus.choices}
    if status not in allowed_status:
        status = ""
    driver = (request.GET.get("driver") or "").strip()
    if not driver.isdigit():
        driver = ""
    assignment = (request.GET.get("driver_assignment") or "").strip().lower()
    if assignment not in ("", "assigned", "unassigned"):
        assignment = ""
    planner_from = (request.GET.get("planner_from") or "").strip()
    if parse_date(planner_from) is None:
        planner_from = ""
    planner_to = (request.GET.get("planner_to") or "").strip()
    if parse_date(planner_to) is None:
        planner_to = ""
    return status, driver, assignment, planner_from, planner_to


def _driver_list_sidebar_filters(request) -> tuple[str, str, str]:
    """GET filters: active (yes/no), company (fleet_company slug), driveroo (yes/no/req/unset)."""
    active = (request.GET.get("active") or "").strip().lower()
    if active not in ("", "yes", "no"):
        active = ""
    company = (request.GET.get("company") or "").strip()
    fleet_allowed = {k for k, _ in DispatchDriver.FleetCompany.choices}
    if company not in fleet_allowed:
        company = ""
    driveroo = (request.GET.get("driveroo") or "").strip().lower()
    if driveroo not in ("", "yes", "no", "req", "unset"):
        driveroo = ""
    return active, company, driveroo


@permission_required("dispatch.view")
def driver_list(request):
    drivers = DispatchDriver.objects.select_related("dispatcher").order_by(
        "sort_order", "last_name", "first_name"
    )
    filter_active, filter_company, filter_driveroo = _driver_list_sidebar_filters(request)
    if filter_active == "yes":
        drivers = drivers.filter(is_active=True)
    elif filter_active == "no":
        drivers = drivers.filter(is_active=False)
    if filter_company:
        drivers = drivers.filter(fleet_company=filter_company)
    if filter_driveroo == "unset":
        drivers = drivers.filter(Q(driveroo_status="") | Q(driveroo_status__isnull=True))
    elif filter_driveroo in (DispatchDriver.DriverooStatus.YES, DispatchDriver.DriverooStatus.NO, DispatchDriver.DriverooStatus.REQ):
        drivers = drivers.filter(driveroo_status=filter_driveroo)

    q = _search_q(request)
    if q:
        drivers = drivers.filter(driver_search_q(q)).distinct()

    paginator = Paginator(drivers, DISPATCH_DRIVER_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    attach_current_equipment_to_drivers(page_obj.object_list)

    filters_active = bool(q or filter_active or filter_company or filter_driveroo)

    return render(
        request,
        "dispatch/driver_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "search_q": q,
            "filter_active": filter_active,
            "filter_company": filter_company,
            "filter_driveroo": filter_driveroo,
            "filters_active": filters_active,
            "fleet_company_choices": DispatchDriver.FleetCompany.choices,
            "driveroo_choices": DispatchDriver.DriverooStatus.choices,
            "filter_querystring": _driver_list_filter_querystring(request),
            "can_manage_dispatch": has_permission_for_user_context(request.user, "dispatch.manage"),
        },
    )


@permission_required("dispatch.view")
def truck_list(request):
    trucks = DispatchTruck.objects.order_by("unit_number")
    filter_active, filter_assignment = _truck_trailer_list_filters(request)
    if filter_active == "yes":
        trucks = trucks.filter(is_active=True)
    elif filter_active == "no":
        trucks = trucks.filter(is_active=False)
    assigned_ids = assigned_truck_ids()
    if filter_assignment == "assigned":
        trucks = trucks.filter(pk__in=assigned_ids)
    elif filter_assignment == "unassigned":
        trucks = trucks.exclude(pk__in=assigned_ids)

    q = _search_q(request)
    if q:
        trucks = trucks.filter(truck_search_q(q)).distinct()

    paginator = Paginator(trucks, DISPATCH_TRUCK_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    attach_current_driver_to_trucks(page_obj.object_list)
    filters_active = bool(q or filter_active or filter_assignment)

    return render(
        request,
        "dispatch/truck_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "search_q": q,
            "filter_active": filter_active,
            "filter_assignment": filter_assignment,
            "filters_active": filters_active,
            "filter_querystring": _filter_querystring_without_page(request),
            "can_manage_dispatch": has_permission_for_user_context(request.user, "dispatch.manage"),
        },
    )


@permission_required("dispatch.view")
def trailer_list(request):
    trailers = DispatchTrailer.objects.order_by("unit_number")
    filter_active, filter_assignment = _truck_trailer_list_filters(request)
    if filter_active == "yes":
        trailers = trailers.filter(is_active=True)
    elif filter_active == "no":
        trailers = trailers.filter(is_active=False)
    assigned_ids = assigned_trailer_ids()
    if filter_assignment == "assigned":
        trailers = trailers.filter(pk__in=assigned_ids)
    elif filter_assignment == "unassigned":
        trailers = trailers.exclude(pk__in=assigned_ids)

    q = _search_q(request)
    if q:
        trailers = trailers.filter(trailer_search_q(q)).distinct()

    paginator = Paginator(trailers, DISPATCH_TRAILER_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    attach_current_driver_to_trailers(page_obj.object_list)
    filters_active = bool(q or filter_active or filter_assignment)

    return render(
        request,
        "dispatch/trailer_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "search_q": q,
            "filter_active": filter_active,
            "filter_assignment": filter_assignment,
            "filters_active": filters_active,
            "filter_querystring": _filter_querystring_without_page(request),
            "can_manage_dispatch": has_permission_for_user_context(request.user, "dispatch.manage"),
        },
    )


@permission_required("dispatch.view")
def driver_detail(request, pk: int):
    driver = get_object_or_404(
        DispatchDriver.objects.select_related("dispatcher"),
        pk=pk,
    )
    attach_current_equipment_to_drivers([driver])
    can_manage_dispatch = has_permission_for_user_context(request.user, "dispatch.manage")
    ctx = {
        "hide_header_and_footer": False,
        "driver": driver,
        "current_assignments": current_assignments_for_driver(driver),
        "assignment_history": assignment_history_for_driver(driver),
        "unavailability_entries": driver.unavailability_entries.all()[:30],
        "can_manage_dispatch": can_manage_dispatch,
    }
    if can_manage_dispatch:
        ctx["truck_choices"] = DispatchTruck.objects.filter(is_active=True).order_by("unit_number")
        ctx["trailer_choices"] = DispatchTrailer.objects.filter(is_active=True).order_by("unit_number")
    return render(request, "dispatch/driver_detail.html", ctx)


@permission_required("dispatch.view")
def truck_detail(request, pk: int):
    truck = get_object_or_404(DispatchTruck, pk=pk)
    attach_current_driver_to_trucks([truck])
    can_manage_dispatch = has_permission_for_user_context(request.user, "dispatch.manage")
    ctx = {
        "hide_header_and_footer": False,
        "truck": truck,
        "current_assignment": (
            current_assignments()
            .filter(truck=truck)
            .select_related("driver", "driver__dispatcher", "trailer")
            .order_by("-started_at", "-pk")
            .first()
        ),
        "assignment_history": assignment_history_for_truck(truck),
        "can_manage_dispatch": can_manage_dispatch,
    }
    if can_manage_dispatch:
        ctx["driver_choices"] = DispatchDriver.objects.filter(is_active=True).order_by(
            "sort_order", "last_name", "first_name"
        )
        ctx["trailer_choices"] = DispatchTrailer.objects.filter(is_active=True).order_by(
            "unit_number"
        )
    ctx["samsara_panel_url"] = reverse("dispatch:truck_samsara_panel", kwargs={"pk": truck.pk})
    return render(request, "dispatch/truck_detail.html", ctx)


@permission_required("dispatch.view")
def truck_detail_samsara_panel(request, pk: int):
    """Lazy-loaded Samsara tab: DB context + live API (GPS, fuel, engine, faults)."""
    truck = get_object_or_404(DispatchTruck, pk=pk)
    attach_current_driver_to_trucks([truck])
    current_assignment = (
        current_assignments()
        .filter(truck=truck)
        .select_related("driver", "driver__dispatcher", "trailer")
        .order_by("-started_at", "-pk")
        .first()
    )
    ctx = {
        "truck": truck,
        "can_manage_dispatch": has_permission_for_user_context(
            request.user, "dispatch.manage"
        ),
        "current_assignment": current_assignment,
    }
    ctx.update(
        samsara_context_for_truck(
            truck,
            current_assignment=current_assignment,
            refresh_live=bool(request.GET.get("refresh")),
        )
    )
    return render(request, "dispatch/_truck_detail_samsara.html", ctx)


@permission_required("dispatch.view")
def trailer_detail(request, pk: int):
    trailer = get_object_or_404(DispatchTrailer, pk=pk)
    attach_current_driver_to_trailers([trailer])
    can_manage_dispatch = has_permission_for_user_context(request.user, "dispatch.manage")
    ctx = {
        "hide_header_and_footer": False,
        "trailer": trailer,
        "current_assignment": (
            current_assignments()
            .filter(trailer=trailer)
            .select_related("driver", "driver__dispatcher", "truck")
            .order_by("-started_at", "-pk")
            .first()
        ),
        "assignment_history": assignment_history_for_trailer(trailer),
        "can_manage_dispatch": can_manage_dispatch,
    }
    if can_manage_dispatch:
        ctx["driver_choices"] = DispatchDriver.objects.filter(is_active=True).order_by(
            "sort_order", "last_name", "first_name"
        )
        ctx["truck_choices"] = DispatchTruck.objects.filter(is_active=True).order_by("unit_number")
    return render(request, "dispatch/trailer_detail.html", ctx)


@permission_required("dispatch.manage")
def driver_import_sample(request):
    resp = HttpResponse(sample_csv_bytes(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="dispatch_drivers_sample.csv"'
    return resp


@permission_required("dispatch.manage")
def driver_import(request):
    summary = None
    if request.method == "POST":
        upload = request.FILES.get("csv_file")
        if not upload:
            messages.error(request, "Choose a CSV file.")
        else:
            rows, err = parse_csv_file(upload)
            if err:
                messages.error(request, err)
            else:
                summary = import_drivers_from_rows(rows)
                messages.success(
                    request,
                    f"Import finished: {summary.created} created, {summary.updated} updated, "
                    f"{summary.skipped} skipped.",
                )
                if summary.errors:
                    messages.warning(
                        request,
                        f"{len(summary.errors)} row(s) had issues — see the list below.",
                    )
    return render(
        request,
        "dispatch/driver_import.html",
        {
            "hide_header_and_footer": False,
            "import_summary": summary,
        },
    )


@permission_required("dispatch.manage")
def driver_create(request):
    if request.method == "POST":
        form = DispatchDriverForm(request.POST)
    else:
        form = DispatchDriverForm()
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": True,
        "driver": None,
        "form_action": reverse("dispatch:driver_create"),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request, reverse("dispatch:driver_list"), "Driver saved."
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/driver_form.html",
        modal_template="dispatch/driver_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
def driver_edit(request, pk: int):
    driver = get_object_or_404(DispatchDriver, pk=pk)
    if request.method == "POST":
        form = DispatchDriverForm(request.POST, instance=driver)
    else:
        form = DispatchDriverForm(instance=driver)
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": False,
        "driver": driver,
        "form_action": reverse("dispatch:driver_edit", kwargs={"pk": driver.pk}),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request,
            reverse("dispatch:driver_detail", kwargs={"pk": driver.pk}),
            "Driver updated.",
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/driver_form.html",
        modal_template="dispatch/driver_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
def driver_unavailability_create(request, driver_pk: int):
    driver = get_object_or_404(DispatchDriver, pk=driver_pk)
    if request.method == "POST":
        form = DriverUnavailabilityForm(request.POST)
    else:
        initial = {}
        raw_start = (request.GET.get("start") or "").strip()
        if raw_start:
            parsed = _parse_planner_date(raw_start)
            if parsed:
                initial["start_date"] = parsed
                initial["end_date"] = parsed
        form = DriverUnavailabilityForm(initial=initial)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.driver = driver
        entry.save()
        messages.success(request, "Driver unavailability saved.")
        return redirect("dispatch:driver_detail", pk=driver.pk)
    return render(
        request,
        "dispatch/driver_unavailability_form.html",
        {
            "hide_header_and_footer": False,
            "form": form,
            "driver": driver,
            "entry": None,
            "is_edit": False,
        },
    )


@permission_required("dispatch.manage")
def driver_unavailability_edit(request, driver_pk: int, pk: int):
    driver = get_object_or_404(DispatchDriver, pk=driver_pk)
    entry = get_object_or_404(DriverUnavailability, pk=pk, driver=driver)
    if request.method == "POST":
        form = DriverUnavailabilityForm(request.POST, instance=entry)
    else:
        form = DriverUnavailabilityForm(instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Driver unavailability updated.")
        return redirect("dispatch:driver_detail", pk=driver.pk)
    return render(
        request,
        "dispatch/driver_unavailability_form.html",
        {
            "hide_header_and_footer": False,
            "form": form,
            "driver": driver,
            "entry": entry,
            "is_edit": True,
        },
    )


@permission_required("dispatch.manage")
@require_POST
def driver_unavailability_delete(request, driver_pk: int, pk: int):
    driver = get_object_or_404(DispatchDriver, pk=driver_pk)
    entry = get_object_or_404(DriverUnavailability, pk=pk, driver=driver)
    entry.delete()
    messages.success(request, "Driver unavailability removed.")
    return redirect("dispatch:driver_detail", pk=driver.pk)


@permission_required("dispatch.manage")
def truck_create(request):
    if request.method == "POST":
        form = DispatchTruckForm(request.POST)
    else:
        form = DispatchTruckForm()
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": True,
        "truck": None,
        "form_action": reverse("dispatch:truck_create"),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request, reverse("dispatch:truck_list"), "Truck saved."
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/truck_form.html",
        modal_template="dispatch/truck_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
def truck_edit(request, pk: int):
    truck = get_object_or_404(DispatchTruck, pk=pk)
    attach_current_driver_to_trucks([truck])
    if request.method == "POST":
        form = DispatchTruckForm(request.POST, instance=truck)
    else:
        form = DispatchTruckForm(instance=truck)
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": False,
        "truck": truck,
        "form_action": reverse("dispatch:truck_edit", kwargs={"pk": truck.pk}),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request,
            reverse("dispatch:truck_detail", kwargs={"pk": truck.pk}),
            "Truck updated.",
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/truck_form.html",
        modal_template="dispatch/truck_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
def trailer_create(request):
    if request.method == "POST":
        form = DispatchTrailerForm(request.POST)
    else:
        form = DispatchTrailerForm()
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": True,
        "trailer": None,
        "form_action": reverse("dispatch:trailer_create"),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request, reverse("dispatch:trailer_list"), "Trailer saved."
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/trailer_form.html",
        modal_template="dispatch/trailer_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
def trailer_edit(request, pk: int):
    trailer = get_object_or_404(DispatchTrailer, pk=pk)
    attach_current_driver_to_trailers([trailer])
    if request.method == "POST":
        form = DispatchTrailerForm(request.POST, instance=trailer)
    else:
        form = DispatchTrailerForm(instance=trailer)
    ctx = {
        "hide_header_and_footer": False,
        "form": form,
        "is_create": False,
        "trailer": trailer,
        "form_action": reverse("dispatch:trailer_edit", kwargs={"pk": trailer.pk}),
    }
    if request.method == "POST" and form.is_valid():
        form.save()
        return _dispatch_entity_form_success(
            request,
            reverse("dispatch:trailer_detail", kwargs={"pk": trailer.pk}),
            "Trailer updated.",
        )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/trailer_form.html",
        modal_template="dispatch/trailer_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.view")
def load_list(request):
    loads = DispatchLoad.objects.select_related("driver", "driver__dispatcher").order_by(
        "-planner_date", "-created_at", "pk"
    )
    filter_status, filter_driver, filter_driver_assignment, filter_planner_from, filter_planner_to = (
        _load_list_filters(request)
    )
    if filter_status:
        loads = loads.filter(status=filter_status)
    if filter_driver:
        loads = loads.filter(driver_id=int(filter_driver))
    if filter_driver_assignment == "assigned":
        loads = loads.filter(driver_id__isnull=False)
    elif filter_driver_assignment == "unassigned":
        loads = loads.filter(driver_id__isnull=True)
    if filter_planner_from:
        loads = loads.filter(planner_date__gte=filter_planner_from)
    if filter_planner_to:
        loads = loads.filter(planner_date__lte=filter_planner_to)

    q = _search_q(request)
    if q:
        loads = loads.filter(load_search_q(q)).distinct()

    paginator = Paginator(loads, DISPATCH_LOAD_LIST_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    attach_current_equipment_to_drivers({ld.driver for ld in page_obj.object_list if ld.driver_id})

    filters_active = bool(
        q
        or filter_status
        or filter_driver
        or filter_driver_assignment
        or filter_planner_from
        or filter_planner_to
    )

    return render(
        request,
        "dispatch/load_list.html",
        {
            "hide_header_and_footer": False,
            "page_obj": page_obj,
            "search_q": q,
            "filter_status": filter_status,
            "filter_driver": filter_driver,
            "filter_driver_assignment": filter_driver_assignment,
            "filter_planner_from": filter_planner_from,
            "filter_planner_to": filter_planner_to,
            "filters_active": filters_active,
            "load_status_choices": LoadStatus.choices,
            "driver_choices": DispatchDriver.objects.filter(is_active=True).order_by(
                "last_name", "first_name", "pk"
            ),
            "filter_querystring": _filter_querystring_without_page(request),
            "can_manage_dispatch": has_permission_for_user_context(request.user, "dispatch.manage"),
        },
    )


@permission_required("dispatch.view")
def load_detail(request, pk: int):
    load = get_object_or_404(
        DispatchLoad.objects.select_related("driver", "driver__dispatcher").prefetch_related(
            Prefetch(
                "status_history",
                queryset=DispatchLoadStatusHistory.objects.select_related("changed_by").order_by(
                    "-changed_at", "-pk"
                ),
            ),
            Prefetch(
                "comments",
                queryset=DispatchLoadComment.objects.select_related("created_by").order_by(
                    "-created_at", "-pk"
                ),
            ),
        ),
        pk=pk,
    )
    driver_truck = None
    driver_trailers: list[DispatchTrailer] = []
    if load.driver_id:
        attach_current_equipment_to_drivers([load.driver])
        driver_truck = load.driver.truck
        driver_trailers = list(load.driver.trailers.all())
    can_manage = has_permission_for_user_context(request.user, "dispatch.manage")
    history_chronological = list(load.status_history.all())
    history_chronological.reverse()
    history_to_statuses = [row.to_status for row in history_chronological]
    status_workflow_steps, off_workflow_status = workflow_steps_for_load(
        load.status,
        history_to_statuses=history_to_statuses,
    )
    return render(
        request,
        "dispatch/load_detail.html",
        {
            "hide_header_and_footer": False,
            "load": load,
            "driver_truck": driver_truck,
            "driver_trailers": driver_trailers,
            "load_status_choices": LoadStatus.choices,
            "rc_status_choices": RCStatus.choices,
            "pod_status_choices": PODStatus.choices,
            "load_status_update_url": reverse("dispatch:load_status_update", kwargs={"pk": load.pk}),
            "load_docs_status_update_url": reverse(
                "dispatch:load_docs_status_update", kwargs={"pk": load.pk}
            ),
            "can_manage_dispatch": can_manage,
            "comments": load.comments.all(),
            "status_workflow_steps": status_workflow_steps,
            "off_workflow_status": off_workflow_status,
            "status_history_timeline": history_chronological,
        },
    )


@permission_required("dispatch.view")
@require_GET
def load_comments(request, pk: int):
    """JSON list of comments for planner dialog / AJAX."""
    load = get_object_or_404(DispatchLoad, pk=pk)
    comments = (
        load.comments.select_related("created_by")
        .order_by("-created_at", "-pk")[:200]
    )
    return JsonResponse(
        {
            "ok": True,
            "load_id": load.pk,
            "comments": [serialize_load_comment(c) for c in comments],
        }
    )


@permission_required("dispatch.view")
@require_POST
def load_comment_create(request, pk: int):
    """Add a comment; JSON for planner, redirect for load detail form."""
    load = get_object_or_404(DispatchLoad, pk=pk)
    body = (request.POST.get("body") or "").strip()
    if not body:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "Comment cannot be empty."}, status=400)
        messages.error(request, "Comment cannot be empty.")
        return redirect(request.POST.get("next") or reverse("dispatch:load_detail", kwargs={"pk": pk}))
    if len(body) > 5000:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "Comment is too long (max 5000 characters)."}, status=400)
        messages.error(request, "Comment is too long (max 5000 characters).")
        return redirect(request.POST.get("next") or reverse("dispatch:load_detail", kwargs={"pk": pk}))

    comment = DispatchLoadComment.objects.create(
        load=load,
        body=body,
        created_by=request.user,
    )
    payload = serialize_load_comment(comment)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "comment": payload, "comment_count": load.comments.count()})

    messages.success(request, "Comment added.")
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("dispatch:load_detail", pk=pk)


def _parse_planner_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _load_form_context(
    *,
    form,
    load=None,
    is_create: bool,
    assignment_driver=None,
    pickup_date=None,
    form_action: str,
):
    return {
        "hide_header_and_footer": False,
        "form": form,
        "load": load,
        "is_create": is_create,
        "assignment_driver": assignment_driver,
        "pickup_date": pickup_date,
        "form_action": form_action,
    }


@permission_required("dispatch.manage")
def load_create(request):
    raw_driver = (request.GET.get("driver") or request.POST.get("driver_id") or "").strip()
    raw_date = (
        request.GET.get("planner_date")
        or request.POST.get("grid_pickup_date")
        or ""
    ).strip()
    pickup_day = _parse_planner_date(raw_date)

    assignment_driver = None
    if raw_driver.isdigit():
        assignment_driver = get_object_or_404(
            DispatchDriver.objects.select_related("dispatcher"),
            pk=int(raw_driver),
        )

    if request.method == "POST":
        form = DispatchLoadForm(request.POST, pickup_date=pickup_day)
    else:
        form = DispatchLoadForm(pickup_date=pickup_day)
        if assignment_driver:
            preview_dates = [pickup_day] if pickup_day else []
            for message in validate_driver_assignment_for_load(
                assignment_driver,
                check_dates=preview_dates,
            ):
                messages.error(request, message)

    if request.method == "POST" and form.is_valid():
        load = form.save(commit=False)
        if assignment_driver:
            load.driver = assignment_driver
        elif not load.driver_id:
            load.driver = None
        if load.driver_id:
            driver = assignment_driver
            if driver is None or driver.pk != load.driver_id:
                driver = DispatchDriver.objects.select_related("dispatcher").get(
                    pk=load.driver_id
                )
            schedule_dates = collect_load_schedule_dates(load, anchor_date=pickup_day)
            for message in validate_driver_assignment_for_load(
                driver,
                check_dates=schedule_dates,
            ):
                form.add_error(None, message)
        if not form.errors:
            load.save()
            record_load_status_change(
                load=load,
                from_status="",
                to_status=load.status,
                user=request.user,
                source=SOURCE_LOAD_CREATE,
            )
            return _dispatch_entity_form_success(
                request,
                reverse("dispatch:load_detail", kwargs={"pk": load.pk}),
                "Load created.",
            )

    ctx = _load_form_context(
        form=form,
        is_create=True,
        assignment_driver=assignment_driver,
        pickup_date=pickup_day,
        form_action=reverse("dispatch:load_create"),
    )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/load_form.html",
        modal_template="dispatch/load_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.manage")
@require_POST
def load_docs_status_update(request, pk: int):
    """Quick RC / POD status change from load detail (AJAX)."""
    load = get_object_or_404(DispatchLoad, pk=pk)
    update_fields: list[str] = []
    if "rc_status" in request.POST:
        raw_rc = (request.POST.get("rc_status") or "").strip()
        if raw_rc not in {c[0] for c in RCStatus.choices}:
            return JsonResponse({"ok": False, "error": "Invalid RC status."}, status=400)
        load.rc_status = raw_rc
        update_fields.append("rc_status")
    if "pod_status" in request.POST:
        raw_pod = (request.POST.get("pod_status") or "").strip()
        if raw_pod not in {c[0] for c in PODStatus.choices}:
            return JsonResponse({"ok": False, "error": "Invalid POD status."}, status=400)
        load.pod_status = raw_pod
        update_fields.append("pod_status")
    if not update_fields:
        return JsonResponse({"ok": False, "error": "No status provided."}, status=400)
    update_fields.append("updated_at")
    load.save(update_fields=update_fields)
    return JsonResponse(
        {
            "ok": True,
            "id": load.pk,
            "rc_status": load.get_rc_status_display(),
            "rc_status_slug": load.rc_status,
            "rc_status_badge_css_class": load.rc_status_badge_css_class(),
            "pod_status": load.get_pod_status_display(),
            "pod_status_slug": load.pod_status,
            "pod_status_badge_css_class": load.pod_status_badge_css_class(),
        }
    )


@permission_required("dispatch.manage")
@require_POST
def load_status_update(request, pk: int):
    """Quick status change from planner or load detail (AJAX)."""
    load = get_object_or_404(DispatchLoad, pk=pk)
    raw = (request.POST.get("status") or "").strip()
    valid = {choice[0] for choice in LoadStatus.choices}
    if raw not in valid:
        return JsonResponse({"ok": False, "error": "Invalid status."}, status=400)
    raw_source = (request.POST.get("source") or "").strip()
    allowed_sources = {SOURCE_PLANNER, SOURCE_LOAD_DETAIL}
    source = raw_source if raw_source in allowed_sources else SOURCE_PLANNER
    apply_load_status_change(
        load=load,
        to_status=raw,
        user=request.user,
        source=source,
    )
    return JsonResponse(
        {
            "ok": True,
            "id": load.pk,
            "status": load.get_status_display(),
            "status_slug": load.status,
            "status_css_class": load.planner_status_css_class(),
            "status_badge_css_class": load.status_badge_css_class(),
        }
    )


@permission_required("dispatch.manage")
def load_edit(request, pk: int):
    load = get_object_or_404(
        DispatchLoad.objects.select_related("driver", "driver__dispatcher"),
        pk=pk,
    )
    if request.method == "POST":
        form = DispatchLoadForm(request.POST, instance=load)
    else:
        form = DispatchLoadForm(instance=load)
    if request.method == "POST" and form.is_valid():
        old_status = load.status
        load = form.save(commit=False)
        if load.driver_id:
            driver = load.driver
            if driver is None:
                driver = DispatchDriver.objects.select_related("dispatcher").get(
                    pk=load.driver_id
                )
            for message in validate_driver_assignment_for_load(
                driver,
                check_dates=collect_load_schedule_dates(load),
            ):
                form.add_error(None, message)
        if form.errors:
            ctx = _load_form_context(
                form=form,
                load=load,
                is_create=False,
                assignment_driver=load.driver,
                pickup_date=load.pickup_planner_date(),
                form_action=reverse("dispatch:load_edit", kwargs={"pk": load.pk}),
            )
            return _render_dispatch_entity_form(
                request,
                full_template="dispatch/load_form.html",
                modal_template="dispatch/load_form_modal.html",
                ctx=ctx,
            )
        load.save()
        record_load_status_change(
            load=load,
            from_status=old_status,
            to_status=load.status,
            user=request.user,
            source=SOURCE_LOAD_FORM,
        )
        return _dispatch_entity_form_success(
            request,
            reverse("dispatch:load_detail", kwargs={"pk": load.pk}),
            "Load updated.",
        )
    ctx = _load_form_context(
        form=form,
        load=load,
        is_create=False,
        assignment_driver=load.driver,
        pickup_date=load.pickup_planner_date(),
        form_action=reverse("dispatch:load_edit", kwargs={"pk": load.pk}),
    )
    return _render_dispatch_entity_form(
        request,
        full_template="dispatch/load_form.html",
        modal_template="dispatch/load_form_modal.html",
        ctx=ctx,
    )


@permission_required("dispatch.view")
def trip_list_redirect(request):
    return redirect("dispatch:load_list")


@permission_required("dispatch.view")
def trip_detail_redirect(request, pk: int):
    if DispatchLoad.objects.filter(pk=pk).exists():
        return redirect("dispatch:load_detail", pk=pk)
    return redirect("dispatch:load_list")


@permission_required("dispatch.manage")
def trip_create_redirect(request):
    q = request.GET.urlencode()
    url = reverse("dispatch:load_create")
    if q:
        url = f"{url}?{q}"
    return redirect(url)


@permission_required("dispatch.manage")
def trip_edit_redirect(request, pk: int):
    if DispatchLoad.objects.filter(pk=pk).exists():
        return redirect("dispatch:load_edit", pk=pk)
    return redirect("dispatch:load_list")


@permission_required("dispatch.manage")
def trip_status_update_redirect(request, pk: int):
    return load_status_update(request, pk)


@permission_required("dispatch.manage")
def trip_load_status_redirect(request, trip_pk: int, load_pk: int):
    return load_status_update(request, load_pk)


@permission_required("dispatch.manage")
def trip_load_add_redirect(request, trip_pk: int):
    return redirect("dispatch:load_detail", pk=trip_pk) if DispatchLoad.objects.filter(pk=trip_pk).exists() else redirect("dispatch:load_list")


@permission_required("dispatch.manage")
def trip_load_edit_redirect(request, trip_pk: int, load_pk: int):
    return redirect("dispatch:load_edit", pk=load_pk) if DispatchLoad.objects.filter(pk=load_pk).exists() else redirect("dispatch:load_list")


def _parse_optional_pk(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


@permission_required("dispatch.manage")
def truck_assign_equipment(request, pk: int):
    """Save driver and/or trailer for a truck (driver optional)."""
    truck = get_object_or_404(DispatchTruck, pk=pk)
    if request.method != "POST":
        return redirect("dispatch:truck_detail", pk=truck.pk)

    action = (request.POST.get("action") or "").strip()
    next_url = (request.POST.get("next") or "").strip()
    if action != "save_equipment":
        return HttpResponseBadRequest("Unknown action.")

    driver = None
    trailer = None
    driver_pk = _parse_optional_pk(request.POST.get("driver"))
    trailer_pk = _parse_optional_pk(request.POST.get("trailer"))
    if driver_pk:
        driver = get_object_or_404(DispatchDriver, pk=driver_pk)
    if trailer_pk:
        trailer = get_object_or_404(DispatchTrailer, pk=trailer_pk)

    set_truck_equipment(truck, driver=driver, trailer=trailer)

    parts = [f"truck {truck.unit_number}"]
    if driver:
        parts.append(f"driver {driver.display_name}")
    if trailer:
        parts.append(f"trailer {trailer.unit_number}")
    messages.success(request, f"Equipment updated: {', '.join(parts)}.")

    if next_url.startswith("/dispatch/"):
        return redirect(next_url)
    return redirect("dispatch:truck_detail", pk=truck.pk)


@permission_required("dispatch.manage")
def trailer_assign_equipment(request, pk: int):
    """Save truck and/or driver for a trailer (both optional)."""
    trailer = get_object_or_404(DispatchTrailer, pk=pk)
    if request.method != "POST":
        return redirect("dispatch:trailer_detail", pk=trailer.pk)

    action = (request.POST.get("action") or "").strip()
    next_url = (request.POST.get("next") or "").strip()
    if action != "save_equipment":
        return HttpResponseBadRequest("Unknown action.")

    driver = None
    truck = None
    driver_pk = _parse_optional_pk(request.POST.get("driver"))
    truck_pk = _parse_optional_pk(request.POST.get("truck"))
    if driver_pk:
        driver = get_object_or_404(DispatchDriver, pk=driver_pk)
    if truck_pk:
        truck = get_object_or_404(DispatchTruck, pk=truck_pk)

    set_trailer_equipment(trailer, driver=driver, truck=truck)

    parts = [f"trailer {trailer.unit_number}"]
    if truck:
        parts.append(f"truck {truck.unit_number}")
    if driver:
        parts.append(f"driver {driver.display_name}")
    messages.success(request, f"Equipment updated: {', '.join(parts)}.")

    if next_url.startswith("/dispatch/"):
        return redirect(next_url)
    return redirect("dispatch:trailer_detail", pk=trailer.pk)


@permission_required("dispatch.manage")
def driver_assign_equipment(request, pk: int):
    """Save truck and trailer for a driver in one step (assignment history)."""
    driver = get_object_or_404(DispatchDriver, pk=pk)
    if request.method != "POST":
        return redirect("dispatch:driver_detail", pk=driver.pk)

    action = (request.POST.get("action") or "").strip()
    next_url = (request.POST.get("next") or "").strip()

    if action != "save_equipment":
        return HttpResponseBadRequest("Unknown action.")

    truck_pk = (request.POST.get("truck") or "").strip()
    trailer_pk = (request.POST.get("trailer") or "").strip()
    truck = None
    trailer = None
    if truck_pk.isdigit():
        truck = get_object_or_404(DispatchTruck, pk=int(truck_pk))
    if trailer_pk.isdigit():
        trailer = get_object_or_404(DispatchTrailer, pk=int(trailer_pk))

    set_driver_equipment(driver, truck=truck, trailer=trailer)

    parts = []
    if truck:
        parts.append(f"truck {truck.unit_number}")
    if trailer:
        parts.append(f"trailer {trailer.unit_number}")
    if parts:
        messages.success(request, f"Equipment updated: {', '.join(parts)}.")
    else:
        messages.success(request, "All equipment unassigned.")

    if next_url.startswith("/dispatch/"):
        return redirect(next_url)
    return redirect("dispatch:driver_detail", pk=driver.pk)


@permission_required("dispatch.manage")
def assignment_end(request, pk: int):
    """End a current assignment row (keeps history, sets ended_at)."""
    assignment = get_object_or_404(DispatchAssignment, pk=pk, ended_at__isnull=True)
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    assignment.ended_at = timezone.now()
    assignment.save(update_fields=["ended_at"])
    messages.success(request, "Assignment ended.")

    if next_url.startswith("/dispatch/"):
        return redirect(next_url)
    if assignment.driver_id:
        return redirect("dispatch:driver_detail", pk=assignment.driver_id)
    if assignment.truck_id:
        return redirect("dispatch:truck_detail", pk=assignment.truck_id)
    if assignment.trailer_id:
        return redirect("dispatch:trailer_detail", pk=assignment.trailer_id)
    return redirect("dispatch:planner")
