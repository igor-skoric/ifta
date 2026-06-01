from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_trip_status_history(apps, schema_editor):
    DispatchTrip = apps.get_model("dispatch", "DispatchTrip")
    DispatchTripStatusHistory = apps.get_model("dispatch", "DispatchTripStatusHistory")
    rows = [
        DispatchTripStatusHistory(
            trip_id=trip.pk,
            from_status="",
            to_status=trip.status,
            changed_at=trip.created_at,
            source="backfill",
        )
        for trip in DispatchTrip.objects.all().only("pk", "status", "created_at")
    ]
    if rows:
        DispatchTripStatusHistory.objects.bulk_create(rows, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0023_merge_20260519_1555"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DispatchTripStatusHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
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
                        help_text="Empty for the initial status on create or backfill.",
                        max_length=32,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
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
                        max_length=32,
                    ),
                ),
                ("changed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("source", models.CharField(blank=True, max_length=32)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dispatch_trip_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_history",
                        to="dispatch.dispatchtrip",
                    ),
                ),
            ],
            options={
                "verbose_name": "trip status history",
                "verbose_name_plural": "trip status history",
                "ordering": ["-changed_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="dispatchtripstatushistory",
            index=models.Index(fields=["trip", "-changed_at"], name="dispatch_di_trip_id_0a8f2e_idx"),
        ),
        migrations.RunPython(backfill_trip_status_history, migrations.RunPython.noop),
    ]
