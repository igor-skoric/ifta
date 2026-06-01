from django.db import migrations


def seed_defaults(apps, schema_editor):
    AccountDepartment = apps.get_model("accounts", "AccountDepartment")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    departments = [
        ("tracking", "Tracking"),
        ("hr", "HR"),
        ("it", "IT"),
        ("safety", "Safety"),
        ("dispatch", "Dispatch"),
        ("recruiter", "Recruiter"),
        ("finance", "Finance"),
    ]
    for code, name in departments:
        AccountDepartment.objects.get_or_create(code=code, defaults={"name": name, "is_active": True})

    default_roles = {
        "ifta_viewer": ["ifta.view"],
        "ifta_operator": ["ifta.view", "ifta.manage_uploads"],
        "statistics_viewer": ["statistics.view"],
        "office_viewer": ["office.view_map", "office.view_people", "office.view_inventory"],
        "office_manager": ["office.view_map", "office.view_people", "office.manage_people", "office.view_inventory", "office.manage_inventory"],
        "security_admin": ["accounts.manage_users", "accounts.manage_roles"],
    }
    for slug, permissions in default_roles.items():
        role, _ = Role.objects.get_or_create(
            slug=slug,
            defaults={"name": slug.replace("_", " ").title(), "description": "System role", "is_system": True},
        )
        for code in permissions:
            RolePermission.objects.get_or_create(role=role, code=code)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, migrations.RunPython.noop),
    ]

