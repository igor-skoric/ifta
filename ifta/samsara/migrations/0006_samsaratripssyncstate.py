# Generated manually for incremental trips sync watermark.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("samsara", "0005_rename_samsara_trip_drv_start_idx_samsara_sam_driver__313761_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="SamsaraTripsSyncState",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "last_query_end_ms",
                    models.BigIntegerField(
                        blank=True,
                        null=True,
                        help_text="End of last successful trips API window (Unix ms). Next incremental run starts from this minus overlap.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Samsara trips sync state",
            },
        ),
    ]
