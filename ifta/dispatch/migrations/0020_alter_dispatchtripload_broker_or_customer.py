from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0019_dispatchtripload_pickup_datetime"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispatchtripload",
            name="broker_or_customer",
            field=models.CharField(
                blank=True,
                help_text="Primary reference for this load (broker load #, internal ID, etc.).",
                max_length=200,
                verbose_name="Load ID",
            ),
        ),
    ]
