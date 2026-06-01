from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0018_alter_dispatchassignment_driver_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchtripload",
            name="pickup_datetime",
            field=models.DateTimeField(
                blank=True,
                help_text="Scheduled pick-up date and time for this load (required for 2nd+ loads on a trip).",
                null=True,
            ),
        ),
    ]
