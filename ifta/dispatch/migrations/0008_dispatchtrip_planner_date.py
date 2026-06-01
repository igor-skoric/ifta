# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0007_dispatchtrip_dispatchtripload"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchtrip",
            name="planner_date",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Calendar day this trip appears on the load planner for the assigned driver.",
                null=True,
            ),
        ),
    ]
