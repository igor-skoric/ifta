import re
from collections import defaultdict
from typing import Any

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils.text import slugify

from .models import Department, OfficeDirectoryEmployee

_HEADER_ALIASES = {
    "department": "department",
    "dept": "department",
    "team": "department",
    "name": "name",
    "employee_name": "name",
    "full_name": "name",
    "email": "work_email",
    "e_mail": "work_email",
    "mail": "work_email",
    "work_email": "work_email",
    "company_email": "work_email",
    "business_email": "work_email",
    "corp_email": "work_email",
    "private_email": "private_email",
    "personal_email": "private_email",
    "home_email": "private_email",
    "phone": "work_phone",
    "telephone": "work_phone",
    "work_phone": "work_phone",
    "company_phone": "work_phone",
    "office_phone": "work_phone",
    "business_phone": "work_phone",
    "private_phone": "private_phone",
    "personal_phone": "private_phone",
    "home_phone": "private_phone",
    "cell": "private_phone",
    "cell_phone": "private_phone",
    "mobile_phone": "private_phone",
    "location": "location",
    "office": "location",
    "country": "location",
    "position": "position",
    "title": "position",
    "role": "position",
    "job_title": "position",
}


def _norm_header(h: Any) -> str:
    s = str(h).strip().lower()
    s = re.sub(r"[\s\.]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s.strip("_")


def _canonical_field(header_norm: str) -> str | None:
    h = header_norm.strip("_")
    return _HEADER_ALIASES.get(h)


def _field_to_labels(columns: list) -> dict[str, list[str]]:
    """Redosled kolona u Excelu: prva neprazna vrednost za dato polje."""
    out: dict[str, list[str]] = defaultdict(list)
    for col in columns:
        label = str(col)
        field = _canonical_field(_norm_header(label))
        if field:
            out[field].append(label)
    return dict(out)


def _cell_first_nonempty(row: Any, labels: list[str] | None) -> Any:
    if not labels:
        return None
    for lab in labels:
        if lab not in row.index:
            continue
        v = row[lab]
        if isinstance(v, float) and pd.isna(v):
            continue
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _clean_phone(raw: Any) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    if not s or s.upper() in {"N/A", "NA", "-", "—", "NONE"}:
        return ""
    return s[:30]


def _clean_email(raw: Any) -> tuple[str, bool]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return "", True
    s = str(raw).strip().lower()
    if not s or s in {"n/a", "na", "-", "none"}:
        return "", True
    s = s[:254]
    try:
        validate_email(s)
    except ValidationError:
        return "", False
    return s, True


def _split_name(cell: Any) -> tuple[str, str, str | None]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return "", "", None
    s = str(cell).strip()
    if not s:
        return "", "", None
    if "@" in s:
        email_candidate = s.lower().replace(" ", "")
        try:
            validate_email(email_candidate)
        except ValidationError:
            pass
        else:
            local = email_candidate.split("@", 1)[0]
            local_norm = local.replace(".", " ").replace("_", " ").replace("-", " ")
            parts = [p for p in local_norm.split() if p]
            if not parts:
                return "Unknown", "", email_candidate
            first = parts[0].title()
            last = " ".join(p.title() for p in parts[1:]) if len(parts) > 1 else ""
            return first, last, email_candidate
    parts = s.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:]), None
    return parts[0], "", None


def _resolve_department(raw: Any) -> Department | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.upper() in {"N/A", "NA", "-"}:
        return None
    d = Department.objects.filter(name__iexact=s).first()
    if d:
        return d
    code_hyphen = slugify(s)
    d = Department.objects.filter(code=code_hyphen).first()
    if d:
        return d
    code_us = code_hyphen.replace("-", "_")
    d = Department.objects.filter(code=code_us).first()
    if d:
        return d
    return Department.objects.filter(code=s.lower().replace(" ", "_")).first()


def _str_cell(raw: Any, max_len: int) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    return s[:max_len] if s else ""


def _opt_email(s: str) -> str | None:
    s = (s or "").strip()
    return s[:254] if s else None


def _opt_phone(s: str) -> str | None:
    s = (s or "").strip()
    return s[:30] if s else None


def _find_existing_employee(
    *,
    first_name: str,
    last_name: str,
    department: Department | None,
    work_email: str,
    private_email: str,
) -> OfficeDirectoryEmployee | None:
    """
    Uparivanje reda sa zaposlenim bez oslanjanja samo na email (više ljudi može deliti work email).

    Redosled: ime+prezime+departman → ime+prezime+work email → ime+prezime+private email
    → ime+prezime bez departmana (oba null) → work email samo ako je jedinstven u bazi
    → private email samo ako je jedinstven.
    """
    fn, ln = first_name.strip(), (last_name or "").strip()
    if not fn:
        return None

    qs = OfficeDirectoryEmployee.objects.all()

    if department is not None:
        hit = qs.filter(
            first_name__iexact=fn,
            last_name__iexact=ln,
            department=department,
        ).first()
        if hit:
            return hit

    if work_email and "@" in work_email:
        hit = qs.filter(
            first_name__iexact=fn,
            last_name__iexact=ln,
            work_email__iexact=work_email,
        ).first()
        if hit:
            return hit

    if private_email and "@" in private_email:
        hit = qs.filter(
            first_name__iexact=fn,
            last_name__iexact=ln,
            private_email__iexact=private_email,
        ).first()
        if hit:
            return hit

    if department is None:
        hit = qs.filter(
            first_name__iexact=fn,
            last_name__iexact=ln,
            department__isnull=True,
        ).first()
        if hit:
            return hit

    if work_email and "@" in work_email:
        we = qs.filter(work_email__iexact=work_email)
        if we.count() == 1:
            return we.first()

    if private_email and "@" in private_email:
        pe = qs.filter(private_email__iexact=private_email)
        if pe.count() == 1:
            return pe.first()

    return None


def import_employees_from_excel(file) -> dict[str, Any]:
    created = updated = skipped = 0
    errors: list[str] = []
    warnings: list[str] = []

    try:
        df = pd.read_excel(file, sheet_name=0, engine="openpyxl")
    except Exception as e:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": [f"Ne mogu da procitam Excel: {e}"], "warnings": []}

    if df.empty:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Fajl je prazan."], "warnings": []}

    field_labels = _field_to_labels(list(df.columns))
    if "name" not in field_labels:
        errors.append(
            "Nedostaje kolona 'Name' (ili alias). Pronadjene kolone: " + ", ".join(map(str, df.columns))
        )
        return {"created": 0, "updated": 0, "skipped": 0, "errors": errors, "warnings": warnings}

    def pick(row: Any, field: str) -> Any:
        return _cell_first_nonempty(row, field_labels.get(field))

    for row_num, (_, row) in enumerate(df.iterrows(), start=2):
        try:
            name_raw = pick(row, "name")
            fn, ln, work_email_from_name = _split_name(name_raw)
            if not fn and not ln:
                skipped += 1
                warnings.append(f"Red {row_num}: prazno ime — preskoceno.")
                continue

            raw_work_email = pick(row, "work_email")
            we_cell, we_ok = _clean_email(raw_work_email)
            if not we_ok and raw_work_email is not None and str(raw_work_email).strip():
                warnings.append(f"Red {row_num}: nevažeći work email — ignorisan.")

            raw_private_email = pick(row, "private_email")
            pe_cell, pe_ok = _clean_email(raw_private_email)
            if not pe_ok and raw_private_email is not None and str(raw_private_email).strip():
                warnings.append(f"Red {row_num}: nevažeći private email — ignorisan.")

            work_email = we_cell or (work_email_from_name or "")
            if work_email:
                try:
                    validate_email(work_email)
                except ValidationError:
                    warnings.append(f"Red {row_num}: nevažeći work email (Name/kolone) — ignorisan.")
                    work_email = ""

            private_email = pe_cell
            if private_email:
                try:
                    validate_email(private_email)
                except ValidationError:
                    warnings.append(f"Red {row_num}: nevažeći private email — ignorisan.")
                    private_email = ""

            work_phone = _clean_phone(pick(row, "work_phone"))
            private_phone = _clean_phone(pick(row, "private_phone"))

            location = _str_cell(pick(row, "location"), 120)
            position = _str_cell(pick(row, "position"), 80)

            dept_raw = pick(row, "department")
            dept = _resolve_department(dept_raw)
            if dept_raw is not None and str(dept_raw).strip() and dept is None:
                warnings.append(f"Red {row_num}: nepoznat departman '{dept_raw}' — zaposleni bez departmana.")

            with transaction.atomic():
                existing = _find_existing_employee(
                    first_name=fn,
                    last_name=ln or "-",
                    department=dept,
                    work_email=work_email,
                    private_email=private_email,
                )

                payload = {
                    "first_name": fn[:100],
                    "last_name": (ln or "-")[:100],
                    "work_email": _opt_email(work_email),
                    "private_email": _opt_email(private_email),
                    "work_phone": _opt_phone(work_phone),
                    "private_phone": _opt_phone(private_phone),
                    "department": dept,
                    "location": location,
                    "position": position,
                    "is_active": True,
                }

                if existing:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                    existing.save()
                    updated += 1
                else:
                    OfficeDirectoryEmployee.objects.create(**payload)
                    created += 1
        except Exception as e:
            errors.append(f"Red {row_num}: {e}")

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors, "warnings": warnings}
