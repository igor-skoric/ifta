from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispatchdriver",
            name="dispatcher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dispatch_drivers",
                to="office.officedirectoryemployee",
            ),
        ),
    ]
