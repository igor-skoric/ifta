from pathlib import Path
from django.conf import settings
from django.shortcuts import render, get_object_or_404

from django.http import JsonResponse
from .models import Seat, SeatAssignment, AssetAssignment
from django.db.models import Prefetch

SVG_PATH = Path(settings.BASE_DIR) / "static" / "office" / "office_map.svg"


def office_map(request):
    svg_text = SVG_PATH.read_text(encoding="utf-8")

    # 1) Seats
    seats_qs = Seat.objects.all().only("id", "svg_id", "label", "dept", "zone", "seat_no", "is_active")

    # 2) Active SeatAssignment (end_at = NULL) + employee
    active_seat_assignments = SeatAssignment.objects.filter(end_at__isnull=True).select_related("employee").only(
        "id", "seat_id", "employee_id",
        "start_at", "note",
        "employee__id", "employee__alias", "employee__name", "employee__name",
        "employee__email", "employee__phone", "employee__is_active",
    )

    # 3) (Opcionalno) Active assets per employee (end_at = NULL)
    active_asset_assignments = AssetAssignment.objects.filter(end_at__isnull=True).select_related("asset").only(
        "id", "employee_id",
        "asset__id", "asset__asset_type", "asset__brand", "asset__model",
        "asset__serial_number", "asset__inventory_tag", "asset__status",
    )

    # Prefetch na Seat i kroz assignment do employee i assets
    seats_qs = seats_qs.prefetch_related(
        Prefetch("assignments", queryset=active_seat_assignments, to_attr="active_assignments")
    )

    # Učitaj assets mapu employee_id -> [assets]
    assets_by_employee = {}
    for aa in active_asset_assignments:
        assets_by_employee.setdefault(aa.employee_id, []).append({
            "id": aa.asset_id,
            "type": aa.asset.asset_type,
            "brand": aa.asset.brand,
            "model": aa.asset.model,
            "serial_number": aa.asset.serial_number,
            "inventory_tag": aa.asset.inventory_tag,
            "status": aa.asset.status,
        })

    # Build payload za JS
    seats_payload = []
    for s in seats_qs:
        active = s.active_assignments[0] if getattr(s, "active_assignments", []) else None
        emp = active.employee if active else None

        seats_payload.append({
            "svg_id": s.svg_id,
            "label": s.label,
            "dept": s.dept,
            "zone": s.zone,
            "seat_no": s.seat_no,
            "is_active": s.is_active,

            "assignment": None if not active else {
                "start_at": active.start_at.isoformat(),
                "note": active.note,
            },

            "employee": None if not emp else {
                "id": emp.id,
                "alias": emp.alias,
                "name": emp.name,
                "name": emp.name,
                "email": emp.email,
                "phone": emp.phone,
                "is_active": emp.is_active,
                "assets": assets_by_employee.get(emp.id, []),
            },
        })

    return render(request, "office/map.html", {
        "svg_text": svg_text,
        "seats": seats_payload,
    })

