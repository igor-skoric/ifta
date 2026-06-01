from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("leave", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaveAllowance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField()),
                ("granted_days", models.DecimalField(decimal_places=1, default=20, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="leave_allowances", to="office.officedirectoryemployee"),
                ),
            ],
            options={
                "ordering": ["-year", "employee__last_name", "employee__first_name"],
                "unique_together": {("employee", "year")},
            },
        ),
    ]

