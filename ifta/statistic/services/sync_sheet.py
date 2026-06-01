from ..models import WeeklyDayData, SheetConfig, DispatcherSheetRow
from ..sheets.fetch_sheets import company_drivers_weekly
from ..week_scope import current_iso_year_week
from django.utils import timezone
import re
import logging

logger = logging.getLogger(__name__)


def _iso_year_week_or_current(year, iso_week):
    if year is not None and iso_week is not None:
        return int(year), int(iso_week)
    return current_iso_year_week()


def sync_weekly_sheet(
    *,
    code="LIVEBOARD",
    year=None,
    iso_week=None,
    sheet_id=None,
    sheet_range=None,
    tab_name=None,
    touch_config_synced_at=True,
):
    """
    Upsert za jednu ISO nedelju (podrazumevano tekuća).

    Za istorijske sheetove prosledi ``year`` i ``iso_week`` (broj ISO nedelje).
    Opciono ``sheet_id`` / ``sheet_range`` / ``tab_name`` da se ne menja SheetConfig u bazi.
    """
    config = SheetConfig.objects.filter(code=code).first()
    company_drivers_id = sheet_id or (config.sheet_id if config else None)
    range = sheet_range or (config.sheet_range if config else None)
    resolved_tab = tab_name if tab_name is not None else (config.tab_name if config else "")

    if not company_drivers_id or not range:
        logger.warning("sync_weekly_sheet: nedostaje sheet_id ili sheet_range (code=%s)", code)
        return False

    sheet = f"{resolved_tab}{range}"

    rows = company_drivers_weekly(company_drivers_id, sheet)
    if not rows or len(rows) < 2:
        return False

    year, iso_week = _iso_year_week_or_current(year, iso_week)
    days_seen = set()

    for row in rows[1:]:  # preskačemo header
        while len(row) < 5:
            row.append("0")  # popuni prazna polja

        day = row[0].strip()
        gross = float(row[1].replace("$", "").replace(",", "")) if row[1] else 0.0
        cut = float(row[2].replace("$", "").replace(",", "")) if row[2] else 0.0
        miles = int(row[3]) if row[3] else 0
        rate = float(row[4].replace("$", "")) if len(row) > 4 and row[4] else 0.0

        WeeklyDayData.objects.update_or_create(
            year=year,
            iso_week=iso_week,
            day=day,
            defaults={
                "gross": gross,
                "cut": cut,
                "miles": miles,
                "rate_per_mile": rate,
            },
        )
        days_seen.add(day)

    WeeklyDayData.objects.filter(year=year, iso_week=iso_week).exclude(day__in=days_seen).delete()

    if touch_config_synced_at and config:
        config.last_synced_at = timezone.now()
        config.save(update_fields=["last_synced_at"])
    return True


def sync_dispatcher_sheet(
    *,
    code="DISPATCHER_SHEET",
    year=None,
    iso_week=None,
    sheet_id=None,
    sheet_range=None,
    tab_name=None,
    touch_config_synced_at=True,
):
    """
    Upsert dispečera za jednu ISO nedelju (podrazumevano tekuća).

    Za backfill starih sheetova: ``year``, ``iso_week``, opciono override polja sheeta.
    """
    config = SheetConfig.objects.filter(code=code).first()
    resolved_id = sheet_id or (config.sheet_id if config else None)
    sheet_range = sheet_range or (config.sheet_range if config else None)
    resolved_tab = tab_name if tab_name is not None else (config.tab_name if config else "")

    if not resolved_id or not sheet_range:
        logger.warning("sync_dispatcher_sheet: nedostaje sheet_id ili sheet_range (code=%s)", code)
        return False

    sheet_id = resolved_id
    tab_name = resolved_tab
    sheet = f"{tab_name}{sheet_range}"
    rows = company_drivers_weekly(sheet_id, sheet)
    if not rows or len(rows) < 2:
        return False

    headers = rows[0]
    data_rows = rows[1:]
    normalized_headers = [_normalize_header(h) for h in headers]
    header_index = {name: idx for idx, name in enumerate(normalized_headers)}
    gpu_idx = _resolve_header_index(header_index, ["gpu"], 9)
    drpm_idx = _resolve_header_index(header_index, ["drpm", "driverrpm", "driverratepermile"], None)

    if drpm_idx is None:
        expanded_range = _expand_sheet_range_right(sheet_range)
        if expanded_range and expanded_range != sheet_range:
            expanded_sheet = f"{tab_name}{expanded_range}"
            expanded_rows = company_drivers_weekly(sheet_id, expanded_sheet)
            if expanded_rows and len(expanded_rows) >= 2:
                headers = expanded_rows[0]
                data_rows = expanded_rows[1:]
                normalized_headers = [_normalize_header(h) for h in headers]
                header_index = {name: idx for idx, name in enumerate(normalized_headers)}
                gpu_idx = _resolve_header_index(header_index, ["gpu"], 9)
                drpm_idx = _resolve_header_index(header_index, ["drpm", "driverrpm", "driverratepermile"], None)
                logger.warning(
                    "DISPATCHER_SYNC expanded_range_from=%s to=%s to include DRPM",
                    sheet_range,
                    expanded_range,
                )
    logger.warning(
        "DISPATCHER_SYNC headers_raw=%s headers_normalized=%s gpu_idx=%s drpm_idx=%s rows=%s",
        headers,
        normalized_headers,
        gpu_idx,
        drpm_idx,
        len(data_rows),
    )

    year, iso_week = _iso_year_week_or_current(year, iso_week)
    seen_dispatchers = []

    for row_index, row in enumerate(data_rows):
        while len(row) < len(headers):
            row.append("")

        dispatcher = _get_cell_by_names(row, header_index, ["dispatcher"], 1).strip()
        gross = remove_decimals(_get_cell_by_names(row, header_index, ["gross"], 4))
        cut = remove_decimals(_get_cell_by_names(row, header_index, ["cut"], 5))
        miles = remove_decimals(_get_cell_by_names(row, header_index, ["miles"], 6))
        rpm = _get_cell_by_names(row, header_index, ["rpm"], 7)
        gpu = remove_decimals(_get_cell(row, header_index, None, gpu_idx))
        drpm = format_currency_2_decimals(_get_drpm_value(row, header_index, gpu_idx, drpm_idx))

        if _is_zero_or_empty_number(gross):
            continue

        if row_index == 0:
            logger.warning(
                "DISPATCHER_SYNC first_row_raw=%s extracted dispatcher=%s gross=%s cut=%s miles=%s rpm=%s gpu=%s drpm=%s",
                row,
                dispatcher,
                gross,
                cut,
                miles,
                rpm,
                gpu,
                drpm,
            )

        DispatcherSheetRow.objects.update_or_create(
            year=year,
            iso_week=iso_week,
            dispatcher=dispatcher,
            defaults={
                "gross": gross,
                "cut": cut,
                "miles": miles,
                "rpm": rpm,
                "gpu": gpu,
                "drpm": drpm,
            },
        )
        if dispatcher not in seen_dispatchers:
            seen_dispatchers.append(dispatcher)

    if seen_dispatchers:
        DispatcherSheetRow.objects.filter(year=year, iso_week=iso_week).exclude(
            dispatcher__in=seen_dispatchers
        ).delete()

    if touch_config_synced_at and config:
        config.last_synced_at = timezone.now()
        config.save(update_fields=["last_synced_at"])
    return True


def remove_decimals(value):
    if not value:
        return ""

    value = value.replace("$", "").replace(",", "")
    try:
        return f"{int(float(value)):,}"
    except ValueError:
        return value


def format_currency_2_decimals(value):
    if not value:
        return ""

    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        return f"${float(cleaned):.2f}"
    except ValueError:
        return str(value)


def _normalize_header(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())


def _get_cell(row, header_index, field_name, fallback_index):
    idx = header_index.get(field_name, fallback_index)
    if idx is None or idx >= len(row):
        return ""
    return row[idx]


def _get_cell_by_names(row, header_index, field_names, fallback_index):
    for field_name in field_names:
        value = _get_cell(row, header_index, _normalize_header(field_name), None)
        if value != "":
            return value
    return _get_cell(row, header_index, None, fallback_index)


def _resolve_header_index(header_index, field_names, fallback_index):
    for field_name in field_names:
        idx = header_index.get(_normalize_header(field_name))
        if idx is not None:
            return idx
    return fallback_index


def _get_drpm_value(row, header_index, gpu_idx, drpm_idx):
    value = _get_cell(row, header_index, None, drpm_idx)
    if value != "":
        return value

    if gpu_idx is not None:
        value_after_gpu = _get_cell(row, header_index, None, gpu_idx + 1)
        if value_after_gpu != "":
            return value_after_gpu

    return _get_cell_by_names(row, header_index, ["drpm", "driverrpm", "driver_rate_per_mile"], 10)


def _expand_sheet_range_right(sheet_range):
    # Primer: !A1:J46 -> !A1:K46
    match = re.match(r"^(!?)([A-Z]+)(\d*):([A-Z]+)(\d*)$", str(sheet_range or "").strip())
    if not match:
        return sheet_range

    bang, start_col, start_row, end_col, end_row = match.groups()
    next_col = _next_excel_col(end_col)
    return f"{bang}{start_col}{start_row}:{next_col}{end_row}"


def _next_excel_col(col):
    # A -> B, Z -> AA, AZ -> BA
    num = 0
    for ch in col:
        num = num * 26 + (ord(ch) - ord("A") + 1)
    num += 1

    out = []
    while num > 0:
        num, rem = divmod(num - 1, 26)
        out.append(chr(rem + ord("A")))
    return "".join(reversed(out))


def _is_zero_or_empty_number(value):
    cleaned = str(value or "").replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return True
    try:
        return float(cleaned) == 0.0
    except ValueError:
        return True
