# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0010_dispatchtripload_delivery_datetime"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchdriver",
            name="legacy_driver_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Legacy ID from the previous system (for data migration).",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="dispatchdriver",
            name="hire_date",
            field=models.DateField(blank=True, help_text="Date the driver was hired.", null=True),
        ),
        migrations.AddField(
            model_name="dispatchdriver",
            name="driveroo_status",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("no", "No"), ("req", "Req")],
                help_text="Driveroo app: Yes / No / Req.",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="dispatchdriver",
            name="comp_oo_local_legal",
            field=models.CharField(
                blank=True,
                choices=[
                    ("local_il", "LOCAL (IL)"),
                    ("local_il_hook", "LOCAL (IL + HOOK)"),
                    ("oo", "OO"),
                    ("comp_from_525", "COMP FROM 5/25"),
                    ("comp_30", "COMP 30%"),
                    ("comp_35", "COMP 35%"),
                    ("comp_32", "COMP 32%"),
                    ("comp_065_cpm", "COMP 0.65 CPM"),
                    ("comp_075_cpm", "COMP 0.75 CPM"),
                    ("comp_30_bonus", "COMP %30+BONUS"),
                ],
                help_text="COMP / OO / LOCAL / LEGAL classification.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="dispatchdriver",
            name="fleet_company",
            field=models.CharField(
                blank=True,
                choices=[
                    ("fully_triumph", "FULLY TRIUMPH"),
                    ("fully_ilim", "FULLY ILIM"),
                    ("triumph_ilim", "TRIUMPH/ILIM"),
                    ("gns_ilim", "GNS/ILIM"),
                ],
                help_text="Operating company (dropdown).",
                max_length=32,
            ),
        ),
    ]
