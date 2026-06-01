# Generated manually for week-scoped upsert analytics.

from django.db import migrations, models
from django.db.models import Count, Max
from django.utils import timezone


def _iso_year_week_chicago(dt):
    """Match statistic.week_scope: ISO (year, week) in configured week TZ."""
    from statistic.week_scope import current_iso_year_week, week_timezone

    if dt is None:
        return current_iso_year_week()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=timezone.utc)
    d = dt.astimezone(week_timezone()).date()
    ic = d.isocalendar()
    return ic.year, ic.week


def forwards_assign_weekly(apps, schema_editor):
    from statistic.week_scope import current_iso_year_week

    WeeklyDayData = apps.get_model("statistic", "WeeklyDayData")
    y, w = current_iso_year_week()
    WeeklyDayData.objects.all().update(year=y, iso_week=w)


def forwards_assign_dispatcher_and_dedupe(apps, schema_editor):
    DispatcherSheetRow = apps.get_model("statistic", "DispatcherSheetRow")
    to_update = []
    for row in DispatcherSheetRow.objects.all().iterator():
        y, w = _iso_year_week_chicago(row.imported_at)
        if row.year != y or row.iso_week != w:
            row.year = y
            row.iso_week = w
            to_update.append(row)
    if to_update:
        DispatcherSheetRow.objects.bulk_update(to_update, ["year", "iso_week"], batch_size=500)

    dup_groups = (
        DispatcherSheetRow.objects.values("year", "iso_week", "dispatcher")
        .annotate(c=Count("id"), keep_id=Max("id"))
        .filter(c__gt=1)
    )
    for g in dup_groups:
        DispatcherSheetRow.objects.filter(
            year=g["year"],
            iso_week=g["iso_week"],
            dispatcher=g["dispatcher"],
        ).exclude(id=g["keep_id"]).delete()


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("statistic", "0010_delete_activetrucksfinalgross_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="weeklydaydata",
            name="day",
            field=models.CharField(
                choices=[
                    ("Mon", "Monday"),
                    ("Tue", "Tuesday"),
                    ("Wed", "Wednesday"),
                    ("Thu", "Thursday"),
                    ("Fri", "Friday"),
                    ("Sat", "Saturday"),
                    ("Sun", "Sunday"),
                    ("TOTALS", "Totals"),
                ],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="weeklydaydata",
            name="year",
            field=models.PositiveIntegerField(
                help_text="ISO week year",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="weeklydaydata",
            name="iso_week",
            field=models.PositiveSmallIntegerField(
                help_text="ISO week number (1–53)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="weeklydaydata",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_assign_weekly, backwards_noop),
        migrations.AlterField(
            model_name="weeklydaydata",
            name="year",
            field=models.PositiveIntegerField(help_text="ISO week year"),
        ),
        migrations.AlterField(
            model_name="weeklydaydata",
            name="iso_week",
            field=models.PositiveSmallIntegerField(help_text="ISO week number (1–53)"),
        ),
        migrations.AddConstraint(
            model_name="weeklydaydata",
            constraint=models.UniqueConstraint(
                fields=("year", "iso_week", "day"),
                name="statistic_weeklydaydata_year_iso_week_day_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="weeklydaydata",
            index=models.Index(
                fields=["year", "iso_week"],
                name="statistic_wdd_yr_wk_idx",
            ),
        ),
        migrations.AddField(
            model_name="dispatchersheetrow",
            name="year",
            field=models.PositiveIntegerField(
                help_text="ISO week year",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dispatchersheetrow",
            name="iso_week",
            field=models.PositiveSmallIntegerField(
                help_text="ISO week number (1–53)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dispatchersheetrow",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_assign_dispatcher_and_dedupe, backwards_noop),
        migrations.AlterField(
            model_name="dispatchersheetrow",
            name="year",
            field=models.PositiveIntegerField(help_text="ISO week year"),
        ),
        migrations.AlterField(
            model_name="dispatchersheetrow",
            name="iso_week",
            field=models.PositiveSmallIntegerField(help_text="ISO week number (1–53)"),
        ),
        migrations.AddConstraint(
            model_name="dispatchersheetrow",
            constraint=models.UniqueConstraint(
                fields=("year", "iso_week", "dispatcher"),
                name="statistic_dispatchersheet_year_week_dispatcher_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="dispatchersheetrow",
            index=models.Index(
                fields=["year", "iso_week"],
                name="statistic_dsr_yr_wk_idx",
            ),
        ),
    ]
