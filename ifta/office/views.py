from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.templatetags.static import static

from .forms import EmployeeExcelImportForm, EmployeeForm, EquipmentItemForm, EquipmentItemNoteForm
from .models import Department, OfficeDirectoryEmployee, OfficeEquipmentItem
from .people_import import import_employees_from_excel
from accounts.permissions import permission_required
from accounts.services import has_permission_for_user_context
from leave.models import LeaveAllowance, LeaveEntry
from leave.services import format_leave_days_for_display, get_consumed_vacation_days, get_leave_days_breakdown
from datetime import date


def _get_equipment_by_asset_id(asset_id: str) -> OfficeEquipmentItem:
    aid = (asset_id or "").strip()
    if not aid:
        raise Http404
    return get_object_or_404(
        OfficeEquipmentItem.objects.select_related("assigned_employee", "assigned_employee__department"),
        asset_id__iexact=aid,
    )


def _get_employee_by_employee_id(employee_id: str) -> OfficeDirectoryEmployee:
    eid = (employee_id or "").strip()
    if not eid:
        from django.http import Http404

        raise Http404
    return get_object_or_404(
        OfficeDirectoryEmployee.objects.select_related("department"),
        employee_id__iexact=eid,
    )


def _office_floor_plan_pdf_path() -> Path:
    rel = settings.OFFICE_FLOOR_PLAN_PDF
    return Path(settings.BASE_DIR) / "static" / rel


@permission_required("office.view_map")
def office_map(request):
    pdf_path = _office_floor_plan_pdf_path()
    has_pdf = pdf_path.is_file()
    floor_plan_pdf_url = static(settings.OFFICE_FLOOR_PLAN_PDF)
    return render(
        request,
        "office/map.html",
        {
            "hide_header_and_footer": False,
            "has_pdf": has_pdf,
            "floor_plan_pdf_url": floor_plan_pdf_url,
            "floor_plan_svg_url": static("office/office_map.svg"),
        },
    )


@login_required
def people_inventory(request):
    return redirect("office:people_list")


@permission_required("office.view_people")
def people_list(request):
    query = request.GET.get("q", "").strip()
    department = request.GET.get("department", "").strip()
    selected_department_id = None
    if department.isdigit():
        selected_department_id = int(department)
    login_type = request.GET.get("login_type", "")
    status = request.GET.get("status", "")

    employees = OfficeDirectoryEmployee.objects.select_related("department").all()
    if query:
        employees = employees.filter(
            Q(employee_id__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(work_email__icontains=query)
            | Q(private_email__icontains=query)
            | Q(work_phone__icontains=query)
            | Q(private_phone__icontains=query)
            | Q(location__icontains=query)
            | Q(position__icontains=query)
        )
    if selected_department_id is not None:
        employees = employees.filter(department_id=selected_department_id)
    if login_type:
        employees = employees.filter(login_type=login_type)
    if status in {"active", "inactive"}:
        employees = employees.filter(is_active=(status == "active"))

    return render(
        request,
        "office/people_list.html",
        {
            "employees": employees,
            "q": query,
            "selected_department_id": selected_department_id,
            "selected_login_type": login_type,
            "selected_status": status,
            "departments": Department.objects.filter(is_active=True).order_by("sort_order", "name"),
            "login_type_choices": OfficeDirectoryEmployee.LoginType.choices,
            "hide_header_and_footer": False,
        },
    )


@permission_required("office.manage_people")
def people_import_excel(request):
    form = EmployeeExcelImportForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == "POST" and form.is_valid():
        result = import_employees_from_excel(form.cleaned_data["file"])
    return render(
        request,
        "office/people_import.html",
        {"form": form, "result": result, "hide_header_and_footer": False},
    )


@permission_required("office.manage_people")
def people_create(request):
    form = EmployeeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("office:people_list")
    return render(request, "office/people_form.html", {"form": form, "is_edit": False, "hide_header_and_footer": False})


@permission_required("office.manage_people")
def people_edit(request, employee_id):
    employee = _get_employee_by_employee_id(employee_id)
    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("office:people_list")
    return render(request, "office/people_form.html", {"form": form, "is_edit": True, "employee": employee, "hide_header_and_footer": False})


@permission_required("office.view_people")
def people_profile(request, employee_id):
    employee = _get_employee_by_employee_id(employee_id)
    today = date.today()
    year_choices = [today.year, today.year - 1]
    try:
        current_year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        current_year = today.year
    if current_year not in year_choices:
        current_year = today.year
    allowance = LeaveAllowance.objects.filter(employee=employee, year=current_year).first()
    granted_raw = allowance.granted_days if allowance else 0
    consumed_raw = get_consumed_vacation_days(employee, current_year)
    remaining_raw = granted_raw - consumed_raw
    granted_days = format_leave_days_for_display(granted_raw)
    consumed_days = format_leave_days_for_display(consumed_raw)
    remaining_days = format_leave_days_for_display(remaining_raw)
    type_breakdown_raw = get_leave_days_breakdown(employee, current_year)
    leave_type_styles = {
        LeaveEntry.LeaveType.VACATION_FULL: "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/40",
        LeaveEntry.LeaveType.VACATION_MORNING: "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/40",
        LeaveEntry.LeaveType.VACATION_AFTERNOON: "bg-emerald-500/20 text-emerald-100 ring-1 ring-emerald-400/40",
        LeaveEntry.LeaveType.SICKNESS_FULL: "bg-rose-500/20 text-rose-100 ring-1 ring-rose-400/40",
        LeaveEntry.LeaveType.SICKNESS_MORNING: "bg-rose-500/20 text-rose-100 ring-1 ring-rose-400/40",
        LeaveEntry.LeaveType.SICKNESS_AFTERNOON: "bg-rose-500/20 text-rose-100 ring-1 ring-rose-400/40",
        LeaveEntry.LeaveType.MATERNITY_PATERNITY: "bg-violet-500/20 text-violet-100 ring-1 ring-violet-400/40",
        LeaveEntry.LeaveType.COMPASSIONATE: "bg-amber-500/20 text-amber-100 ring-1 ring-amber-400/40",
        LeaveEntry.LeaveType.TOIL: "bg-sky-500/20 text-sky-100 ring-1 ring-sky-400/40",
        LeaveEntry.LeaveType.WORK_FROM_HOME: "bg-cyan-500/20 text-cyan-100 ring-1 ring-cyan-400/40",
        LeaveEntry.LeaveType.BANK_HOLIDAY: "bg-slate-500/30 text-slate-100 ring-1 ring-slate-300/40",
    }
    leave_type_breakdown = [
        {
            "code": code,
            "label": label,
            "value": format_leave_days_for_display(type_breakdown_raw.get(code, 0)),
            "class_name": leave_type_styles.get(code, "bg-white/10 text-slate-100 ring-1 ring-white/20"),
        }
        for code, label in LeaveEntry.LeaveType.choices
    ]

    leave_entries = employee.leave_entries.filter(
        start_date__year__lte=current_year,
        end_date__year__gte=current_year,
    ).order_by("-start_date")
    assigned_equipment = employee.equipment_items.all().order_by("asset_id")

    return render(
        request,
        "office/people_profile.html",
        {
            "employee": employee,
            "current_year": current_year,
            "granted_days": granted_days,
            "consumed_days": consumed_days,
            "remaining_days": remaining_days,
            "leave_type_breakdown": leave_type_breakdown,
            "year_choices": year_choices,
            "leave_entries": leave_entries,
            "assigned_equipment": assigned_equipment,
            "hide_header_and_footer": False,
        },
    )


@permission_required("office.view_inventory")
def inventory_detail(request, asset_id):
    item = _get_equipment_by_asset_id(asset_id)
    note_entries = item.note_entries.select_related("created_by").all()[:500]
    note_form = EquipmentItemNoteForm()
    can_manage_notes = has_permission_for_user_context(request.user, "office.manage_inventory")

    if request.method == "POST":
        if not can_manage_notes:
            return HttpResponseForbidden("Nemate dozvolu da dodajete beleške.")
        note_form = EquipmentItemNoteForm(request.POST)
        if note_form.is_valid():
            n = note_form.save(commit=False)
            n.item = item
            if request.user.is_authenticated:
                n.created_by = request.user
            n.save()
            return redirect("office:inventory_detail", asset_id=item.asset_id)

    return render(
        request,
        "office/inventory_detail.html",
        {
            "item": item,
            "note_entries": note_entries,
            "note_form": note_form,
            "can_manage_notes": can_manage_notes,
            "hide_header_and_footer": False,
        },
    )


@permission_required("office.view_inventory")
def inventory_list(request):
    query = request.GET.get("q", "").strip()
    equipment_type = request.GET.get("equipment_type", "")
    state = request.GET.get("state", "")
    assigned = request.GET.get("assigned", "")

    equipment = OfficeEquipmentItem.objects.select_related("assigned_employee").all()
    if query:
        equipment = equipment.filter(
            Q(asset_id__icontains=query)
            | Q(brand_model__icontains=query)
            | Q(serial_number__icontains=query)
        )
    if equipment_type:
        equipment = equipment.filter(equipment_type=equipment_type)
    if state:
        equipment = equipment.filter(state=state)
    if assigned == "yes":
        equipment = equipment.filter(assigned_employee__isnull=False)
    elif assigned == "no":
        equipment = equipment.filter(assigned_employee__isnull=True)
    return render(
        request,
        "office/inventory_list.html",
        {
            "equipment": equipment,
            "q": query,
            "selected_equipment_type": equipment_type,
            "selected_state": state,
            "selected_assigned": assigned,
            "equipment_type_choices": OfficeEquipmentItem.EquipmentType.choices,
            "equipment_state_choices": OfficeEquipmentItem.ItemState.choices,
            "hide_header_and_footer": False,
        },
    )


@permission_required("office.manage_inventory")
def inventory_create(request):
    form = EquipmentItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        return redirect("office:inventory_detail", asset_id=obj.asset_id)
    return render(request, "office/inventory_form.html", {"form": form, "is_edit": False, "hide_header_and_footer": False})


@permission_required("office.manage_inventory")
def inventory_edit(request, asset_id):
    item = _get_equipment_by_asset_id(asset_id)
    form = EquipmentItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        return redirect("office:inventory_detail", asset_id=obj.asset_id)
    return render(request, "office/inventory_form.html", {"form": form, "is_edit": True, "item": item, "hide_header_and_footer": False})


@require_POST
@permission_required("office.manage_inventory")
def inventory_delete(request, asset_id):
    item = _get_equipment_by_asset_id(asset_id)
    item.delete()
    return redirect("office:inventory_list")
