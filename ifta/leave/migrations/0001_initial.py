from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("office", "0006_officedirectoryemployee_officeequipmentitem"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaveEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "leave_type",
                    models.CharField(
                        choices=[
                            ("L", "Vacation Leave (Full Day)"),
                            ("L1", "Vacation Leave (Morning)"),
                            ("L2", "Vacation Leave (Afternoon)"),
                            ("S", "Sickness Leave (Full Day)"),
                            ("S1", "Sickness Leave (Morning)"),
                            ("S2", "Sickness Leave (Afternoon)"),
                            ("P", "Maternity or Paternity"),
                            ("C", "Compassionate Leave"),
                            ("T", "TOIL (Time Off In Lieu)"),
                            ("W", "Work From Home"),
                            ("B", "Bank Holiday"),
                        ],
                        max_length=2,
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leave_entries",
                        to="office.officedirectoryemployee",
                    ),
                ),
            ],
            options={
                "ordering": ["-start_date", "employee__last_name", "employee__first_name"],
            },
        ),
    ]

