from calendar import month_name, monthrange
from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.permissions import permission_required
from accounts.services import has_permission_for_user_context
from office.models import OfficeDirectoryEmployee

from .forms import LeaveAllowanceForm, LeaveEntryForm
from .models import LeaveAllowance, LeaveEntry
from .services import format_leave_days_for_display, get_consumed_vacation_days, get_leave_days_breakdown


@permission_required("leave.view")
def leave_dashboard(request):
    today = date.today()
    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month
    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year
    if month < 1 or month > 12:
        month = today.month

    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    month_days = [date(year, month, day) for day in range(1, monthrange(year, month)[1] + 1)]

    active_employees = OfficeDirectoryEmployee.objects.filter(is_active=True).order_by("last_name", "first_name")
    leaves = (
        LeaveEntry.objects.select_related("employee")
        .filter(employee__in=active_employees, start_date__lte=month_end, end_date__gte=month_start)
        .order_by("employee__last_name", "employee__first_name", "start_date")
    )
    leaves_by_employee = {}
    for entry in leaves:
        leaves_by_employee.setdefault(entry.employee_id, []).append(entry)

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

    employee_rows = []
    for employee in active_employees:
        employee_entries = leaves_by_employee.get(employee.id, [])
        cells = []
        for day in month_days:
            day_entry = next((entry for entry in employee_entries if entry.start_date <= day <= entry.end_date), None)
            if day_entry:
                cells.append(
                    {
                        "code": day_entry.leave_type,
                        "label": day_entry.get_leave_type_display(),
                        "class_name": leave_type_styles.get(
                            day_entry.leave_type, "bg-white/10 text-slate-100 ring-1 ring-white/20"
                        ),
                    }
                )
            else:
                cells.append(None)
        employee_rows.append({"employee": employee, "cells": cells})

    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year

    legend_items = [
        {"code": code, "label": label, "class_name": leave_type_styles.get(code, "bg-white/10 text-slate-100")}
        for code, label in LeaveEntry.LeaveType.choices
    ]

    context = {
        "hide_header_and_footer": False,
        "current_month_name": month_name[month],
        "current_year": year,
        "month_days": month_days,
        "employee_rows": employee_rows,
        "legend_items": legend_items,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "today": today,
        "can_manage": has_permission_for_user_context(request.user, "leave.manage"),
    }
    return render(request, "leave/dashboard.html", context)


@permission_required("leave.view")
def leave_balances(request):
    today = date.today()
    allowed_years = [today.year, today.year - 1]
    try:
        selected_year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        selected_year = today.year
    if selected_year not in allowed_years:
        selected_year = today.year

    allowances = LeaveAllowance.objects.select_related("employee").filter(year=selected_year).order_by("employee__last_name", "employee__first_name")
    balances = []
    for allowance in allowances:
        consumed = get_consumed_vacation_days(allowance.employee, selected_year)
        remaining = allowance.granted_days - consumed
        type_breakdown_raw = get_leave_days_breakdown(allowance.employee, selected_year)
        type_breakdown = [
            {"code": code, "label": label, "value": format_leave_days_for_display(type_breakdown_raw.get(code, 0))}
            for code, label in LeaveEntry.LeaveType.choices
        ]
        balances.append(
            {
                "allowance": allowance,
                "granted_display": format_leave_days_for_display(allowance.granted_days),
                "consumed": format_leave_days_for_display(consumed),
                "remaining": format_leave_days_for_display(remaining),
                "type_breakdown": type_breakdown,
            }
        )

    return render(
        request,
        "leave/balances.html",
        {
            "hide_header_and_footer": False,
            "balances": balances,
            "selected_year": selected_year,
            "year_choices": allowed_years,
            "leave_type_choices": LeaveEntry.LeaveType.choices,
            "can_manage": has_permission_for_user_context(request.user, "leave.manage"),
        },
    )


@permission_required("leave.manage")
def leave_create(request):
    form = LeaveEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("leave:dashboard")
    return render(request, "leave/form.html", {"form": form, "is_edit": False, "hide_header_and_footer": False})


@permission_required("leave.manage")
def leave_edit(request, pk):
    entry = get_object_or_404(LeaveEntry, pk=pk)
    form = LeaveEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("leave:dashboard")
    return render(
        request,
        "leave/form.html",
        {"form": form, "entry": entry, "is_edit": True, "hide_header_and_footer": False},
    )


@require_POST
@permission_required("leave.manage")
def leave_delete(request, pk):
    entry = get_object_or_404(LeaveEntry, pk=pk)
    entry.delete()
    return redirect("leave:dashboard")


@permission_required("leave.manage")
def leave_allowance_upsert(request):
    form = LeaveAllowanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        employee = form.cleaned_data["employee"]
        year = form.cleaned_data["year"]
        granted_days = form.cleaned_data["granted_days"]
        LeaveAllowance.objects.update_or_create(
            employee=employee,
            year=year,
            defaults={"granted_days": granted_days},
        )
        return redirect("leave:dashboard")
    return render(request, "leave/allowance_form.html", {"form": form, "hide_header_and_footer": False})


@require_POST
@permission_required("leave.manage")
def leave_allowance_update_inline(request, pk):
    allowance = get_object_or_404(LeaveAllowance, pk=pk)
    raw_value = (request.POST.get("granted_days") or "").strip()
    try:
        granted_days = Decimal(raw_value)
    except (InvalidOperation, ValueError):
        granted_days = allowance.granted_days
    if granted_days < 0:
        granted_days = Decimal("0.0")
    allowance.granted_days = granted_days
    allowance.save(update_fields=["granted_days", "updated_at"])

    year = allowance.year
    try:
        year = int(request.POST.get("year", allowance.year))
    except (TypeError, ValueError):
        year = allowance.year
    return redirect(f"{reverse('leave:balances')}?year={year}")

