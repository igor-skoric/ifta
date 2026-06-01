"""End extra current assignment rows per driver; keep one row with latest truck/trailer."""

from django.db import migrations
from django.utils import timezone


def consolidate_current_rows(apps, schema_editor):
    DispatchAssignment = apps.get_model("dispatch", "DispatchAssignment")
    now = timezone.now()
    active = (
        DispatchAssignment.objects.filter(ended_at__isnull=True)
        .order_by("driver_id", "-started_at", "-pk")
        .select_related("truck", "trailer")
    )
    by_driver: dict[int, list] = {}
    for row in active:
        by_driver.setdefault(row.driver_id, []).append(row)

    for driver_id, rows in by_driver.items():
        if len(rows) <= 1:
            continue
        truck = None
        trailer = None
        for row in rows:
            if row.truck_id:
                truck = row.truck
            if row.trailer_id:
                trailer = row.trailer
        for row in rows:
            row.ended_at = now
            row.save(update_fields=["ended_at"])
        DispatchAssignment.objects.create(
            driver_id=driver_id,
            truck=truck,
            trailer=trailer,
            started_at=now,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0016_end_redundant_truck_only_assignments"),
    ]

    operations = [
        migrations.RunPython(consolidate_current_rows, migrations.RunPython.noop),
    ]
