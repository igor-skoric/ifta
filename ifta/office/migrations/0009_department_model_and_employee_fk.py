from django.db import migrations, models
import django.db.models.deletion


def seed_departments(apps, schema_editor):
    Department = apps.get_model("office", "Department")
    rows = [
        (0, "hr", "HR"),
        (1, "payroll", "PAYROLL"),
        (2, "data_entry", "DATA ENTRY"),
        (3, "safety", "SAFETY"),
        (4, "claims", "CLAIMS"),
        (5, "help_line", "HELP LINE"),
        (6, "recruiters", "RECRUITERS"),
        (7, "maintenance", "MAINTENANCE"),
        (8, "dispatch", "DISPATCH"),
        (9, "brokerage", "BROKERAGE"),
        (10, "track_trace", "TRACK & TRACE"),
    ]
    for sort_order, code, name in rows:
        Department.objects.get_or_create(
            code=code,
            defaults={"name": name, "is_active": True, "sort_order": sort_order},
        )


def link_employees_to_department_fk(apps, schema_editor):
    Employee = apps.get_model("office", "OfficeDirectoryEmployee")
    Department = apps.get_model("office", "Department")
    code_map = {
        "tracking": "track_trace",
        "hr": "hr",
        "it": "data_entry",
        "safety": "safety",
        "dispatch": "dispatch",
        "recruiter": "recruiters",
        "finance": "payroll",
    }
    for emp in Employee.objects.all():
        raw = str(emp.department or "").strip()
        if not raw:
            emp.department_tmp_id = None
            emp.save(update_fields=["department_tmp_id"])
            continue
        target_code = code_map.get(raw, raw)
        dept = Department.objects.filter(code=target_code).first() or Department.objects.filter(code=raw).first()
        emp.department_tmp_id = dept.pk if dept else None
        emp.save(update_fields=["department_tmp_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("office", "0008_remove_legacy_seat_asset_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RunPython(seed_departments, migrations.RunPython.noop),
        migrations.AddField(
            model_name="officedirectoryemployee",
            name="department_tmp",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="office.department",
            ),
        ),
        migrations.RunPython(link_employees_to_department_fk, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="officedirectoryemployee",
            name="department",
        ),
        migrations.RenameField(
            model_name="officedirectoryemployee",
            old_name="department_tmp",
            new_name="department",
        ),
    ]
