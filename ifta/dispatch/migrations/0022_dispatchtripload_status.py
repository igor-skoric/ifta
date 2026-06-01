from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispatch", "0021_dispatchtrip_operational_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispatchtripload",
            name="status",
            field=models.CharField(
                choices=[
                    ("load_booked", "Load Booked"),
                    ("heading_to_pickup", "Heading to Pickup"),
                    ("at_pickup", "At Pickup"),
                    ("loaded", "Loaded"),
                    ("in_transit", "In Transit"),
                    ("at_delivery", "At Delivery"),
                    ("delivered", "Delivered"),
                    ("empty", "Empty"),
                    ("layover", "Layover"),
                    ("breakdown", "Breakdown"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="load_booked",
                max_length=32,
            ),
        ),
    ]
