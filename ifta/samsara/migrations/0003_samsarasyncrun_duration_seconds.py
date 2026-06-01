# Generated manually for SamsaraSyncRun.duration_seconds

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("samsara", "0002_samsaratrip_and_syncrun_resource"),
    ]

    operations = [
        migrations.AddField(
            model_name="samsarasyncrun",
            name="duration_seconds",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
