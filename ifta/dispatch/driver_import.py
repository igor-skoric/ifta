"""
CSV mass-import helpers for DispatchDriver (migration / bulk load).

Expected UTF-8 CSV with a header row. Column names are matched case-insensitively;
aliases such as driver_id → legacy_driver_id, company → fleet_company are accepted.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import transaction
from django.utils.dateparse import parse_date

from office.models import OfficeDirectoryEmployee

from .assignments import assign_driver_trailer, assign_driver_truck
from .models import DispatchDriver, DispatchTrailer, DispatchTruck


_HEADER_ALIASES = {
    "driver_id": "legacy_driver_id",
    "legacy_id": "legacy_driver_id",
    "legacy_driver_id": "legacy_driver_id",
    "firstname": "first_name",
    "first_name": "first_name",
    "last_name": "last_name",
    "lastname": "last_name",
    "hire_date": "hire_date",
    "hiredate": "hire_date",
    "driveroo": "driveroo_status",
    "driveroo_status": "driveroo_status",
    "comp": "comp_oo_local_legal",
    "comp_oo": "comp_oo_local_legal",
    "comp_oo_local_legal": "comp_oo_local_legal",
    "comp/oo/local/legal": "comp_oo_local_legal",
    "company": "fleet_company",
    "fleet_company": "fleet_company",
    "dispatcher": "dispatcher_employee_id",
    "dispatcher_employee_id": "dispatcher_employee_id",
    "dispatcher_id": "dispatcher_employee_id",
    "employee_id": "dispatcher_employee_id",
    "sort": "sort_order",
    "sort_order": "sort_order",
    "active": "is_active",
    "is_active": "is_active",
    "truck_unit_number": "truck_unit_number",
    "truck_number": "truck_unit_number",
    "truck_unit": "truck_unit_number",
    "truck": "truck_unit_number",
    "trailer_unit_number": "trailer_unit_number",
    "trailer_number": "trailer_unit_number",
    "trailer_unit": "trailer_unit_number",
    "trailer": "trailer_unit_number",
    "phone": "phone",
    "cell": "phone",
    "mobile": "phone",
    "email": "email",
    "e_mail": "email",
    "rts_fuel_card": "rts_fuel_card",
    "rts_fuel": "rts_fuel_card",
    "fuel_card": "rts_fuel_card",
    "driver_notes": "driver_notes",
    "notes": "driver_notes",
}


def _norm_header(name: str) -> str:
    if name is None:
        return ""
    s = name.strip().lower().replace("\ufeff", "")
    s = re.sub(r"[^\w]+", "_", s)
    s = s.strip("_")
    return _HEADER_ALIASES.get(s, s)


_email_validator = EmailValidator()


def _parse_rts_fuel_card(val: str | None) -> bool | None:
    """yes/no style; empty → None (store as false when creating/updating)."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().lower()
    if s in ("ues",):  # common typo for "yes"
        return True
    return _parse_bool(s)


def _parse_bool(val: str | None) -> bool | None:
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("", "-", "—"):
        return None
    if s in ("1", "true", "yes", "y", "active"):
        return True
    if s in ("0", "false", "no", "n", "inactive"):
        return False
    return None


def _parse_driveroo(val: str | None) -> str:
    if not val or not str(val).strip():
        return ""
    s = str(val).strip().lower()
    if s in ("y", "yes", "1", "true"):
        return DispatchDriver.DriverooStatus.YES
    if s in ("n", "no", "0", "false"):
        return DispatchDriver.DriverooStatus.NO
    if s in ("r", "req", "request", "requested"):
        return DispatchDriver.DriverooStatus.REQ
    if s in dict(DispatchDriver.DriverooStatus.choices):
        return s
    return ""


def _choice_maps():
    comp_slugs = {k for k, _ in DispatchDriver.CompOoLocalLegal.choices}
    comp_by_label = {}
    for k, lab in DispatchDriver.CompOoLocalLegal.choices:
        comp_by_label[lab.lower().strip()] = k
        comp_by_label[k.lower()] = k
    fleet_slugs = {k for k, _ in DispatchDriver.FleetCompany.choices}
    fleet_by_label = {}
    for k, lab in DispatchDriver.FleetCompany.choices:
        fleet_by_label[lab.lower().strip()] = k
        fleet_by_label[k.lower()] = k
    return comp_slugs, comp_by_label, fleet_slugs, fleet_by_label


_COMP_SLUGS, _COMP_BY_LABEL, _FLEET_SLUGS, _FLEET_BY_LABEL = _choice_maps()


def _parse_comp(val: str | None) -> str:
    if not val or not str(val).strip():
        return ""
    s = str(val).strip()
    if s in _COMP_SLUGS:
        return s
    key = s.lower().strip()
    return _COMP_BY_LABEL.get(key, "")


def _parse_fleet(val: str | None) -> str:
    if not val or not str(val).strip():
        return ""
    s = str(val).strip()
    if s in _FLEET_SLUGS:
        return s
    key = s.lower().strip()
    return _FLEET_BY_LABEL.get(key, "")


def _parse_date_cell(val: str | None) -> date | None:
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    d = parse_date(s)
    if d:
        return d
    # Excel-style or US-style minimal support
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            from datetime import datetime as dt

            return dt.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int_cell(val: str | None, default: int = 0) -> int:
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(float(str(val).strip()))
    except ValueError:
        return default


def _validate_driver_email(email: str) -> str | None:
    e = email.strip()
    if not e:
        return ""
    try:
        _email_validator(e)
    except ValidationError:
        return None
    return e[:254]


def _sync_truck_for_driver(driver: DispatchDriver, unit: str) -> None:
    """Ensure truck unit exists and assign to driver (closes prior assignment history)."""
    u = unit.strip()[:64]
    if not u:
        return
    truck = DispatchTruck.objects.filter(unit_number=u).first()
    if not truck:
        truck = DispatchTruck.objects.create(unit_number=u, is_active=True)
    else:
        updates: list[str] = []
        if not truck.is_active:
            truck.is_active = True
            updates.append("is_active")
        if updates:
            truck.save(update_fields=updates)
    assign_driver_truck(driver, truck)


def _sync_trailer_for_driver(driver: DispatchDriver, unit: str) -> None:
    """Ensure trailer unit exists and assign to driver via current assignment."""
    u = unit.strip()[:64]
    if not u:
        return
    trailer = DispatchTrailer.objects.filter(unit_number=u).first()
    if not trailer:
        trailer = DispatchTrailer.objects.create(unit_number=u, is_active=True)
    elif not trailer.is_active:
        trailer.is_active = True
        trailer.save(update_fields=["is_active"])
    assign_driver_trailer(driver, trailer)


def _resolve_dispatcher(employee_id: str | None):
    if not employee_id or not str(employee_id).strip():
        return None
    raw = str(employee_id).strip()
    qs = OfficeDirectoryEmployee.objects.filter(is_active=True, is_dispatcher=True)
    emp = qs.filter(employee_id__iexact=raw).first()
    if emp:
        return emp
    # Fallback: match email
    return qs.filter(work_email__iexact=raw).first()


@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)


def import_drivers_from_rows(rows: list[dict[str, str]]) -> ImportSummary:
    summary = ImportSummary()
    line_no = 1  # header is line 1 in file; first data row is 2
    for raw in rows:
        line_no += 1
        row = {_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}

        fn = (row.get("first_name") or "").strip()
        ln = (row.get("last_name") or "").strip()
        if not fn or not ln:
            summary.errors.append((line_no, "first_name and last_name are required."))
            summary.skipped += 1
            continue

        legacy = (row.get("legacy_driver_id") or "").strip()
        hire = _parse_date_cell(row.get("hire_date"))
        droo_raw = (row.get("driveroo_status") or "").strip()
        droo = _parse_driveroo(droo_raw)
        comp_raw = (row.get("comp_oo_local_legal") or "").strip()
        comp = _parse_comp(comp_raw)
        fleet_raw = (row.get("fleet_company") or "").strip()
        fleet = _parse_fleet(fleet_raw)
        disp_raw = (row.get("dispatcher_employee_id") or "").strip()
        disp = _resolve_dispatcher(disp_raw)
        sort_o = _parse_int_cell(row.get("sort_order"), 0)
        if sort_o < 0:
            sort_o = 0
        active_cell = _parse_bool(row.get("is_active"))
        is_act = True if active_cell is None else active_cell

        phone_s = (row.get("phone") or "").strip()[:40]
        email_raw = (row.get("email") or "").strip()
        if email_raw:
            email_s = _validate_driver_email(email_raw)
            if email_s is None:
                summary.errors.append((line_no, f"Invalid email address: {email_raw!r}"))
                summary.skipped += 1
                continue
        else:
            email_s = ""

        notes_s = (row.get("driver_notes") or "").strip()
        rts_raw = (row.get("rts_fuel_card") or "").strip()
        rts_parsed = _parse_rts_fuel_card(row.get("rts_fuel_card"))
        if rts_raw and rts_parsed is None:
            summary.errors.append((line_no, f"Invalid rts_fuel_card (use yes / no): {rts_raw!r}"))
            summary.skipped += 1
            continue
        rts_fc = False if rts_parsed is None else rts_parsed

        truck_u = (row.get("truck_unit_number") or "").strip()[:64]
        trailer_u = (row.get("trailer_unit_number") or "").strip()[:64]

        if droo_raw and not droo:
            summary.errors.append((line_no, f"Invalid driveroo_status (use yes, no, req): {droo_raw!r}"))
            summary.skipped += 1
            continue
        if comp_raw and not comp:
            summary.errors.append((line_no, f"Unknown comp_oo_local_legal: {comp_raw!r}"))
            summary.skipped += 1
            continue
        if fleet_raw and not fleet:
            summary.errors.append((line_no, f"Unknown fleet_company: {fleet_raw!r}"))
            summary.skipped += 1
            continue
        if disp_raw and disp is None:
            summary.errors.append((line_no, f"Dispatcher not found (employee ID or work email): {disp_raw!r}"))
            summary.skipped += 1
            continue

        fields = {
            "first_name": fn[:80],
            "last_name": ln[:80],
            "legacy_driver_id": legacy[:64] if legacy else "",
            "hire_date": hire,
            "driveroo_status": droo,
            "comp_oo_local_legal": comp,
            "fleet_company": fleet,
            "dispatcher": disp,
            "sort_order": sort_o,
            "is_active": is_act,
            "phone": phone_s,
            "email": email_s,
            "rts_fuel_card": rts_fc,
            "notes": notes_s,
        }

        try:
            with transaction.atomic():
                if legacy:
                    obj, created = DispatchDriver.objects.update_or_create(
                        legacy_driver_id=legacy,
                        defaults={
                            "first_name": fields["first_name"],
                            "last_name": fields["last_name"],
                            "hire_date": fields["hire_date"],
                            "driveroo_status": fields["driveroo_status"],
                            "comp_oo_local_legal": fields["comp_oo_local_legal"],
                            "fleet_company": fields["fleet_company"],
                            "dispatcher": disp,
                            "sort_order": fields["sort_order"],
                            "is_active": fields["is_active"],
                            "phone": fields["phone"],
                            "email": fields["email"],
                            "rts_fuel_card": fields["rts_fuel_card"],
                            "notes": fields["notes"],
                        },
                    )
                else:
                    obj = DispatchDriver.objects.create(
                        first_name=fields["first_name"],
                        last_name=fields["last_name"],
                        legacy_driver_id="",
                        hire_date=fields["hire_date"],
                        driveroo_status=fields["driveroo_status"],
                        comp_oo_local_legal=fields["comp_oo_local_legal"],
                        fleet_company=fields["fleet_company"],
                        dispatcher=disp,
                        sort_order=fields["sort_order"],
                        is_active=fields["is_active"],
                        phone=fields["phone"],
                        email=fields["email"],
                        rts_fuel_card=fields["rts_fuel_card"],
                        notes=fields["notes"],
                    )
                    created = True

                _sync_truck_for_driver(obj, truck_u)
                _sync_trailer_for_driver(obj, trailer_u)

            if created:
                summary.created += 1
            else:
                summary.updated += 1
        except Exception as ex:  # noqa: BLE001 — surface row errors for migration tooling
            summary.errors.append((line_no, str(ex)))
            summary.skipped += 1

    return summary


def parse_csv_file(upload_file: BinaryIO, max_rows: int = 5000) -> tuple[list[dict[str, str]], str | None]:
    """
    Read uploaded CSV. Returns (list of row dicts with normalized keys, error message or None).
    """
    raw = upload_file.read()
    if not raw:
        return [], "Empty file."
    if len(raw) > 4 * 1024 * 1024:
        return [], "File too large (max 4 MB)."

    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return [], "Could not decode file as UTF-8 or Latin-1."

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    if not fieldnames or not any(fieldnames):
        return [], "Missing header row."
    head_norm = {_norm_header(h) for h in fieldnames if h}
    if "first_name" not in head_norm or "last_name" not in head_norm:
        return (
            [],
            "CSV must include columns for first and last name "
            '(e.g. first_name, last_name, "First Name", LASTNAME).',
        )

    rows_out: list[dict[str, str]] = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            return [], f"Too many rows (max {max_rows})."
        normalized: dict[str, str] = {}
        for k, v in row.items():
            nk = _norm_header(k or "")
            if nk:
                normalized[nk] = v.strip() if isinstance(v, str) and v else (v or "")
        rows_out.append(normalized)

    if not rows_out:
        return [], "No data rows after the header."

    return rows_out, None


def sample_csv_bytes() -> bytes:
    lines = [
        "first_name,last_name,legacy_driver_id,phone,email,rts_fuel_card,notes,truck_unit_number,trailer_unit_number,hire_date,driveroo_status,comp_oo_local_legal,fleet_company,dispatcher_employee_id,sort_order,is_active",
        "Jane,Smith,LEG-1001,555-0100,jane@example.com,yes,Sample note,T-101,TRL-9,2023-06-01,yes,local_il,fully_triumph,EMP00001,10,true",
        "John,Doe,,,,no,,T-202,,2024-01-15,no,oo,gns_ilim,,0,true",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8-sig")
