# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0009_merge_20260512_2233"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchtripload",
            name="delivery_datetime",
            field=models.DateTimeField(
                blank=True,
                help_text="Scheduled delivery date and time (optional; complements free-text delivery window).",
                null=True,
            ),
        ),
    ]
