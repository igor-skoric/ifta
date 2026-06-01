"""Move trip fields onto loads and remove DispatchTrip."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_trip_fields_to_loads(apps, schema_editor):
    DispatchTripLoad = apps.get_model("dispatch", "DispatchTripLoad")
    for load in DispatchTripLoad.objects.select_related("trip").iterator():
        trip = load.trip
        if not trip:
            continue
        updates = []
        if trip.driver_id and not load.driver_id:
            load.driver_id = trip.driver_id
            updates.append("driver_id")
        if trip.planner_date and not load.planner_date:
            load.planner_date = trip.planner_date
            updates.append("planner_date")
        if trip.rate_confirmation_source and not load.rate_confirmation_source:
            load.rate_confirmation_source = trip.rate_confirmation_source
            updates.append("rate_confirmation_source")
        if trip.notes and not load.notes:
            load.notes = trip.notes
            updates.append("notes")
        if updates:
            load.save(update_fields=updates)


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0027_rename_dispatch_di_load_id_7c4a91_idx_dispatch_di_load_id_1484c4_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchtripload",
            name="driver",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="loads",
                to="dispatch.dispatchdriver",
            ),
        ),
        migrations.AddField(
            model_name="dispatchtripload",
            name="planner_date",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Calendar day this load appears on the load planner for the assigned driver.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dispatchtripload",
            name="rate_confirmation_source",
            field=models.CharField(
                blank=True,
                help_text="Optional: filename, URL, or document id for future AI (rate confirmation).",
                max_length=512,
            ),
        ),
        migrations.RunPython(copy_trip_fields_to_loads, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="dispatchtripload",
            name="dispatch_di_trip_id_728d5c_idx",
        ),
        migrations.RemoveField(
            model_name="dispatchtripload",
            name="sequence",
        ),
        migrations.RemoveField(
            model_name="dispatchtripload",
            name="trip",
        ),
        migrations.DeleteModel(
            name="DispatchTripStatusHistory",
        ),
        migrations.DeleteModel(
            name="DispatchTrip",
        ),
        migrations.RenameModel(
            old_name="DispatchTripLoad",
            new_name="DispatchLoad",
        ),
        migrations.RenameModel(
            old_name="DispatchTripLoadStatusHistory",
            new_name="DispatchLoadStatusHistory",
        ),
        migrations.AlterModelOptions(
            name="dispatchload",
            options={"ordering": ["-planner_date", "-created_at", "pk"]},
        ),
        migrations.AddIndex(
            model_name="dispatchload",
            index=models.Index(fields=["driver", "planner_date"], name="dispatch_di_driver__loads_idx"),
        ),
    ]
