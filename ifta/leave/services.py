from datetime import date
from decimal import Decimal, InvalidOperation

from .models import LeaveEntry


VACATION_TYPES = {
    LeaveEntry.LeaveType.VACATION_FULL,
    LeaveEntry.LeaveType.VACATION_MORNING,
    LeaveEntry.LeaveType.VACATION_AFTERNOON,
}

HALF_DAY_TYPES = {
    LeaveEntry.LeaveType.VACATION_MORNING,
    LeaveEntry.LeaveType.VACATION_AFTERNOON,
    LeaveEntry.LeaveType.SICKNESS_MORNING,
    LeaveEntry.LeaveType.SICKNESS_AFTERNOON,
}


def overlapping_days(start_date, end_date, year):
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    actual_start = max(start_date, year_start)
    actual_end = min(end_date, year_end)
    if actual_end < actual_start:
        return 0
    return (actual_end - actual_start).days + 1


def get_consumed_vacation_days(employee, year):
    consumed = Decimal("0.0")
    entries = LeaveEntry.objects.filter(
        employee=employee,
        leave_type__in=VACATION_TYPES,
        start_date__year__lte=year,
        end_date__year__gte=year,
    )
    for entry in entries:
        days = overlapping_days(entry.start_date, entry.end_date, year)
        if days <= 0:
            continue
        if entry.leave_type in HALF_DAY_TYPES:
            consumed += Decimal(days) * Decimal("0.5")
        else:
            consumed += Decimal(days)
    return consumed


def get_leave_days_breakdown(employee, year):
    """
    Returns dict keyed by leave code with consumed days in provided year.
    Includes all leave types from model choices.
    """
    breakdown = {code: Decimal("0.0") for code, _ in LeaveEntry.LeaveType.choices}
    entries = LeaveEntry.objects.filter(
        employee=employee,
        start_date__year__lte=year,
        end_date__year__gte=year,
    )
    for entry in entries:
        days = overlapping_days(entry.start_date, entry.end_date, year)
        if days <= 0:
            continue
        entry_value = Decimal(days) * Decimal("0.5") if entry.leave_type in HALF_DAY_TYPES else Decimal(days)
        breakdown[entry.leave_type] = breakdown.get(entry.leave_type, Decimal("0.0")) + entry_value
    return breakdown


def format_leave_days_for_display(value):
    """Celi brojevi kao int (bez .0); inače jedna decimala (npr. pola dana)."""
    if value is None:
        return 0
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return 0
    quantized = d.quantize(Decimal("0.1"))
    if quantized == quantized.to_integral_value():
        return int(quantized)
    return float(quantized)

