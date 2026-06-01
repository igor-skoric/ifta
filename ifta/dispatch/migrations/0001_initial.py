import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("office", "0014_officedirectoryemployee_is_dispatcher"),
    ]

    operations = [
        migrations.CreateModel(
            name="DispatchDriver",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=80)),
                ("last_name", models.CharField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dispatcher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatch_drivers",
                        to="office.officedirectoryemployee",
                    ),
                ),
            ],
            options={
                "ordering": ["dispatcher_id", "sort_order", "last_name", "first_name"],
            },
        ),
        migrations.CreateModel(
            name="DispatchTrailer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_number", models.CharField(max_length=64)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trailers",
                        to="dispatch.dispatchdriver",
                    ),
                ),
            ],
            options={
                "ordering": ["driver_id", "unit_number"],
            },
        ),
        migrations.CreateModel(
            name="DispatchTruck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_number", models.CharField(max_length=64)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "driver",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="truck",
                        to="dispatch.dispatchdriver",
                    ),
                ),
            ],
            options={
                "ordering": ["unit_number"],
            },
        ),
        migrations.AddIndex(
            model_name="dispatchdriver",
            index=models.Index(fields=["dispatcher", "is_active"], name="dispatch_di_dispat_0f7c8e_idx"),
        ),
    ]
