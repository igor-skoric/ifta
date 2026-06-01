import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0030_driver_unavailability"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DispatchLoadComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dispatch_load_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "load",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="dispatch.dispatchload",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(fields=["load", "-created_at"], name="dispatch_di_load_id_cmt_idx")
                ],
            },
        ),
    ]
