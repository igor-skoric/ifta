from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("samsara", "0003_samsarasyncrun_duration_seconds"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="samsaratrip",
            index=models.Index(fields=["driver_samsara_id", "start_time"], name="samsara_trip_drv_start_idx"),
        ),
    ]
