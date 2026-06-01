from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0002_dispatchdriver_dispatcher_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispatchtruck",
            name="driver",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="truck",
                to="dispatch.dispatchdriver",
            ),
        ),
        migrations.AlterField(
            model_name="dispatchtrailer",
            name="driver",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="trailers",
                to="dispatch.dispatchdriver",
            ),
        ),
    ]
