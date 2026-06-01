from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("office", "0007_alter_officeequipmentitem_state"),
    ]

    operations = [
        migrations.DeleteModel(name="SeatAssignment"),
        migrations.DeleteModel(name="AssetAssignment"),
        migrations.DeleteModel(name="Seat"),
        migrations.DeleteModel(name="Asset"),
        migrations.DeleteModel(name="Employee"),
    ]
