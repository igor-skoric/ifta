# Generated manually for DispatchTrip / DispatchTripLoad

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0006_alter_dispatchtrailer_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="DispatchTrip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "reference_number",
                    models.CharField(
                        blank=True,
                        help_text="Trip / trip # from broker or internal ref (optional).",
                        max_length=64,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("planned", "Planned"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "rate_confirmation_source",
                    models.CharField(
                        blank=True,
                        help_text="Optional: filename, URL, or document id for future AI (rate confirmation).",
                        max_length=512,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "driver",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trips",
                        to="dispatch.dispatchdriver",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DispatchTripLoad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveSmallIntegerField(default=0)),
                ("broker_or_customer", models.CharField(blank=True, max_length=200)),
                ("equipment_type", models.CharField(blank=True, max_length=64)),
                ("pickup_city", models.CharField(blank=True, max_length=120)),
                ("pickup_state", models.CharField(blank=True, max_length=64)),
                ("delivery_city", models.CharField(blank=True, max_length=120)),
                ("delivery_state", models.CharField(blank=True, max_length=64)),
                (
                    "pickup_window",
                    models.CharField(
                        blank=True,
                        help_text="Appointment / window text until structured fields exist.",
                        max_length=200,
                    ),
                ),
                ("delivery_window", models.CharField(blank=True, max_length=200)),
                ("loaded_miles", models.PositiveIntegerField(blank=True, null=True)),
                ("linehaul_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("bol_number", models.CharField(blank=True, max_length=64)),
                ("po_number", models.CharField(blank=True, max_length=64)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="loads",
                        to="dispatch.dispatchtrip",
                    ),
                ),
            ],
            options={
                "ordering": ["trip", "sequence", "pk"],
            },
        ),
        migrations.AddIndex(
            model_name="dispatchtripload",
            index=models.Index(fields=["trip", "sequence"], name="dispatch_tripload_trip_seq_idx"),
        ),
    ]
