from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("samsara", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SamsaraTrip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("samsara_id", models.CharField(max_length=64, unique=True)),
                ("vehicle_samsara_id", models.CharField(blank=True, default="", max_length=64)),
                ("driver_samsara_id", models.CharField(blank=True, default="", max_length=64)),
                ("start_time", models.DateTimeField(blank=True, null=True)),
                ("end_time", models.DateTimeField(blank=True, null=True)),
                ("distance_meters", models.FloatField(default=0)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-start_time", "samsara_id"]},
        ),
        migrations.AlterField(
            model_name="samsarasyncrun",
            name="resource",
            field=models.CharField(
                choices=[("vehicles", "Vehicles"), ("drivers", "Drivers"), ("trips", "Trips")],
                max_length=32,
            ),
        ),
    ]
