from django.db import migrations, models

OLD_TO_NEW = {
    "draft": "load_booked",
    "planned": "load_booked",
    "in_progress": "in_transit",
    "completed": "delivered",
    "cancelled": "cancelled",
}


def migrate_trip_statuses(apps, schema_editor):
    DispatchTrip = apps.get_model("dispatch", "DispatchTrip")
    for trip in DispatchTrip.objects.all():
        new_status = OLD_TO_NEW.get(trip.status)
        if new_status and new_status != trip.status:
            trip.status = new_status
            trip.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0020_alter_dispatchtripload_broker_or_customer"),
    ]

    operations = [
        migrations.RunPython(migrate_trip_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dispatchtrip",
            name="status",
            field=models.CharField(
                choices=[
                    ("load_booked", "Load Booked"),
                    ("heading_to_pickup", "Heading to Pickup"),
                    ("at_pickup", "At Pickup"),
                    ("loaded", "Loaded"),
                    ("in_transit", "In Transit"),
                    ("at_delivery", "At Delivery"),
                    ("delivered", "Delivered"),
                    ("empty", "Empty"),
                    ("layover", "Layover"),
                    ("breakdown", "Breakdown"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="load_booked",
                max_length=32,
            ),
        ),
    ]
