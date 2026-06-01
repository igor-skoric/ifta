from django.db import migrations


def seed_dispatch_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    office_manager = Role.objects.filter(slug="office_manager").first()
    if office_manager:
        RolePermission.objects.get_or_create(role=office_manager, code="dispatch.view")
        RolePermission.objects.get_or_create(role=office_manager, code="dispatch.manage")

    office_viewer = Role.objects.filter(slug="office_viewer").first()
    if office_viewer:
        RolePermission.objects.get_or_create(role=office_viewer, code="dispatch.view")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_userprofile_department"),
    ]

    operations = [
        migrations.RunPython(seed_dispatch_permissions, migrations.RunPython.noop),
    ]
