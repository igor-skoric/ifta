# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("samsara", "0007_alter_samsaratripssyncstate_last_query_end_ms"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="samsaratrip",
            index=models.Index(fields=["vehicle_samsara_id", "start_time"], name="samsara_trip_veh_start_idx"),
        ),
    ]
