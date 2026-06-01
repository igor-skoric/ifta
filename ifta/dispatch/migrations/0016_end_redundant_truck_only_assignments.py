"""Close duplicate current rows: truck-only slot when a trailer row exists for same driver+truck."""

from django.db import migrations
from django.utils import timezone


def end_redundant_truck_only_rows(apps, schema_editor):
    DispatchAssignment = apps.get_model("dispatch", "DispatchAssignment")
    now = timezone.now()
    active = DispatchAssignment.objects.filter(ended_at__isnull=True, trailer__isnull=True)
    for bare in active.select_related("driver", "truck"):
        if not bare.truck_id:
            continue
        has_trailer_row = DispatchAssignment.objects.filter(
            ended_at__isnull=True,
            driver_id=bare.driver_id,
            truck_id=bare.truck_id,
            trailer__isnull=False,
        ).exists()
        if has_trailer_row:
            bare.ended_at = now
            bare.save(update_fields=["ended_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0015_rename_dispatch_di_driver__a1b2c3_idx_dispatch_di_driver__dbeed5_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(end_redundant_truck_only_rows, migrations.RunPython.noop),
    ]
