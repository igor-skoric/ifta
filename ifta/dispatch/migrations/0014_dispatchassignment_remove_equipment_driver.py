from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def copy_driver_links_to_assignments(apps, schema_editor):
    DispatchTruck = apps.get_model("dispatch", "DispatchTruck")
    DispatchTrailer = apps.get_model("dispatch", "DispatchTrailer")
    DispatchAssignment = apps.get_model("dispatch", "DispatchAssignment")
    now = timezone.now()

    for truck in DispatchTruck.objects.filter(driver_id__isnull=False).iterator():
        DispatchAssignment.objects.create(
            driver_id=truck.driver_id,
            truck_id=truck.pk,
            trailer_id=None,
            started_at=now,
        )

    for trailer in DispatchTrailer.objects.filter(driver_id__isnull=False).iterator():
        truck_id = (
            DispatchTruck.objects.filter(driver_id=trailer.driver_id)
            .values_list("pk", flat=True)
            .first()
        )
        DispatchAssignment.objects.create(
            driver_id=trailer.driver_id,
            truck_id=truck_id,
            trailer_id=trailer.pk,
            started_at=now,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0013_alter_dispatchdriver_fleet_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="DispatchAssignment",
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
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="dispatch.dispatchdriver",
                    ),
                ),
                (
                    "trailer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments",
                        to="dispatch.dispatchtrailer",
                    ),
                ),
                (
                    "truck",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments",
                        to="dispatch.dispatchtruck",
                    ),
                ),
            ],
            options={
                "verbose_name": "dispatch assignment",
                "verbose_name_plural": "dispatch assignments",
                "ordering": ["-started_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="dispatchassignment",
            index=models.Index(fields=["driver", "ended_at"], name="dispatch_di_driver__a1b2c3_idx"),
        ),
        migrations.AddIndex(
            model_name="dispatchassignment",
            index=models.Index(fields=["truck", "ended_at"], name="dispatch_di_truck_i_d4e5f6_idx"),
        ),
        migrations.AddIndex(
            model_name="dispatchassignment",
            index=models.Index(fields=["trailer", "ended_at"], name="dispatch_di_trailer_g7h8i9_idx"),
        ),
        migrations.RunPython(copy_driver_links_to_assignments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="dispatchtruck",
            name="driver",
        ),
        migrations.RemoveField(
            model_name="dispatchtrailer",
            name="driver",
        ),
    ]
