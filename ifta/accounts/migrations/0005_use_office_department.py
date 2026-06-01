from django.db import migrations, models
import django.db.models.deletion


def copy_role_departments_to_office(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    OfficeDepartment = apps.get_model("office", "Department")
    code_map = {
        "recruiter": "recruiters",
        "finance": "payroll",
        "tracking": "track_trace",
        "it": "data_entry",
    }
    for role in Role.objects.all():
        for ad in role.allowed_departments.all():
            target = code_map.get(ad.code, ad.code)
            od = OfficeDepartment.objects.filter(code=target).first()
            if od:
                role.allowed_office_departments.add(od)


def migrate_user_profiles_department(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    AccountDepartment = apps.get_model("accounts", "AccountDepartment")
    OfficeDepartment = apps.get_model("office", "Department")
    code_map = {
        "recruiter": "recruiters",
        "finance": "payroll",
        "tracking": "track_trace",
        "it": "data_entry",
    }
    for profile in UserProfile.objects.exclude(department_id=None):
        try:
            ad = AccountDepartment.objects.get(pk=profile.department_id)
        except AccountDepartment.DoesNotExist:
            continue
        target = code_map.get(ad.code, ad.code)
        od = OfficeDepartment.objects.filter(code=target).first()
        if od:
            profile.department_tmp_id = od.pk
            profile.save(update_fields=["department_tmp_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_seed_leave_permissions"),
        ("office", "0009_department_model_and_employee_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="allowed_office_departments",
            field=models.ManyToManyField(blank=True, related_name="roles", to="office.department"),
        ),
        migrations.RunPython(copy_role_departments_to_office, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="role",
            name="allowed_departments",
        ),
        migrations.RenameField(
            model_name="role",
            old_name="allowed_office_departments",
            new_name="allowed_departments",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="department_tmp",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="office.department",
            ),
        ),
        migrations.RunPython(migrate_user_profiles_department, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="userprofile",
            name="department",
        ),
        migrations.RenameField(
            model_name="userprofile",
            old_name="department_tmp",
            new_name="department",
        ),
        migrations.DeleteModel(
            name="AccountDepartment",
        ),
    ]
