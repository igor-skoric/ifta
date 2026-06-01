from django.db import migrations


def add_canada_provinces(apps, schema_editor):
    State = apps.get_model("app", "State")
    provinces = [
        ("ON", "Ontario"),
        ("NB", "New Brunswick"),
    ]
    for code, name in provinces:
        State.objects.get_or_create(code=code, defaults={"name": name})


def remove_canada_provinces(apps, schema_editor):
    State = apps.get_model("app", "State")
    State.objects.filter(code__in=["ON", "NB"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_insert_states'),  # zavisi od poslednje migracije
    ]

    operations = [
        migrations.RunPython(add_canada_provinces, remove_canada_provinces),
    ]
