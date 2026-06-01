from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0017_consolidate_duplicate_current_assignments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispatchassignment",
            name="driver",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assignments",
                to="dispatch.dispatchdriver",
            ),
        ),
    ]
