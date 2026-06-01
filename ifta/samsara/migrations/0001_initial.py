from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SamsaraDriver",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("samsara_id", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(blank=True, default="", max_length=255)),
                ("username", models.CharField(blank=True, default="", max_length=255)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "username", "samsara_id"]},
        ),
        migrations.CreateModel(
            name="SamsaraSyncRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource", models.CharField(choices=[("vehicles", "Vehicles"), ("drivers", "Drivers")], max_length=32)),
                ("success", models.BooleanField(default=False)),
                ("fetched_count", models.PositiveIntegerField(default=0)),
                ("upserted_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SamsaraVehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("samsara_id", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(blank=True, default="", max_length=255)),
                ("external_ids", models.JSONField(blank=True, default=dict)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "samsara_id"]},
        ),
    ]
