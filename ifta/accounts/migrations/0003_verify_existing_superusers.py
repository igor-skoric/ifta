from django.db import migrations


def verify_existing_superusers(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    for user in User.objects.filter(is_superuser=True):
        profile, _ = UserProfile.objects.get_or_create(user_id=user.id)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_defaults"),
    ]

    operations = [
        migrations.RunPython(verify_existing_superusers, migrations.RunPython.noop),
    ]

