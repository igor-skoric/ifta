from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ifta.models import VehicleRecord
from office.models import OfficeDirectoryEmployee, OfficeEquipmentItem


@login_required
def dashboard_home(request):
    employees_total = OfficeDirectoryEmployee.objects.count()
    employees_active = OfficeDirectoryEmployee.objects.filter(is_active=True).count()
    equipment_total = OfficeEquipmentItem.objects.count()
    equipment_assigned = OfficeEquipmentItem.objects.filter(assigned_employee__isnull=False).count()
    equipment_types = OfficeEquipmentItem.objects.values("equipment_type").distinct().count()

    vehicle_records = VehicleRecord.objects.count()
    unique_vehicles = VehicleRecord.objects.values("vehicle").distinct().count()
    unique_jurisdictions = VehicleRecord.objects.values("jurisdiction").distinct().count()

    context = {
        "hide_header_and_footer": False,
        "cards": [
            {
                "title": "Broj zaposlenih",
                "value": employees_total,
                "meta": f"Aktivno: {employees_active}",
                "icon": "fa-users",
            },
            {
                "title": "Broj opreme",
                "value": equipment_total,
                "meta": f"Zaduzena oprema: {equipment_assigned}",
                "icon": "fa-laptop",
            },
            {
                "title": "Tipovi opreme",
                "value": equipment_types,
                "meta": "Broj razlicitih tipova u inventaru",
                "icon": "fa-layer-group",
            },
            {
                "title": "Vozila",
                "value": unique_vehicles,
                "meta": f"IFTA zapisa: {vehicle_records}",
                "icon": "fa-truck",
            },
            {
                "title": "Jurisdikcije",
                "value": unique_jurisdictions,
                "meta": "Ukupno drzava/provincija u IFTA podacima",
                "icon": "fa-map",
            },
        ],
    }
    return render(request, "dashboard/home.html", context)

