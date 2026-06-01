from django.db import migrations


def seed_leave_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    office_manager = Role.objects.filter(slug="office_manager").first()
    if office_manager:
        RolePermission.objects.get_or_create(role=office_manager, code="leave.view")
        RolePermission.objects.get_or_create(role=office_manager, code="leave.manage")

    office_viewer = Role.objects.filter(slug="office_viewer").first()
    if office_viewer:
        RolePermission.objects.get_or_create(role=office_viewer, code="leave.view")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_verify_existing_superusers"),
    ]

    operations = [
        migrations.RunPython(seed_leave_permissions, migrations.RunPython.noop),
    ]

