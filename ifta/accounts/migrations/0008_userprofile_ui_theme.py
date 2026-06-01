from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_seed_dispatch_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="ui_theme",
            field=models.CharField(
                choices=[("dark", "Noćni (tamni)"), ("light", "Dnevni (svetli)")],
                default="dark",
                max_length=16,
            ),
        ),
    ]
