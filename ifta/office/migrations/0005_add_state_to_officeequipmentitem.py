from django.db import migrations


def add_state_column_if_possible(apps, schema_editor):
    conn = schema_editor.connection
    table_name = "app_equipmentitem"

    with conn.cursor() as cursor:
        existing_tables = set(conn.introspection.table_names(cursor))
        if table_name not in existing_tables:
            return

        columns = {
            c.name
            for c in conn.introspection.get_table_description(cursor, table_name)
        }
        if "state" not in columns:
            cursor.execute(
                "ALTER TABLE app_equipmentitem "
                "ADD COLUMN state varchar(20) NOT NULL DEFAULT 'draft'"
            )

        cursor.execute(
            "UPDATE app_equipmentitem "
            "SET state = 'active' "
            "WHERE state = 'in_service'"
        )
        cursor.execute(
            "UPDATE app_equipmentitem "
            "SET state = 'draft' "
            "WHERE state = 'in_stock'"
        )


def noop_reverse(apps, schema_editor):
    # Keeping reverse as no-op for safety on SQLite.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("office", "0004_rename_last_name_employee_name_and_more"),
        ("app", "0009_employee_equipmentitem"),
    ]

    operations = [
        migrations.RunPython(add_state_column_if_possible, noop_reverse),
    ]
