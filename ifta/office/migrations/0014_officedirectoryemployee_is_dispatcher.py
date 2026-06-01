from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("office", "0013_officeequipmentitemnote"),
    ]

    operations = [
        migrations.AddField(
            model_name="officedirectoryemployee",
            name="is_dispatcher",
            field=models.BooleanField(
                default=False,
                help_text="If true, appears on Dispatch load planner and can own driver rows.",
            ),
        ),
    ]
