import argparse

from django.core.management.base import BaseCommand, CommandError

from statistic.services.sync_sheet import sync_dispatcher_sheet, sync_weekly_sheet


class Command(BaseCommand):
    help = (
        "Import one Google Sheet into a chosen ISO calendar week (same upsert as auto sync). "
        "Uses SheetConfig (sheet_id, range, tab) unless you pass overrides. "
        "For old snapshots you need: sheet id from URL, range/tab like production, "
        "and which ISO week that snapshot represents."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "kind",
            choices=("weekly", "dispatcher"),
            help="weekly=LIVEBOARD day rows; dispatcher=DISPATCHER_SHEET",
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="ISO week-year (e.g. 2025; week 1 around New Year may differ from calendar year).",
        )
        parser.add_argument(
            "--iso-week",
            type=int,
            required=True,
            dest="iso_week",
            help="ISO week number 1-53.",
        )
        parser.add_argument(
            "--code",
            default=None,
            help="SheetConfig.code if not LIVEBOARD / DISPATCHER_SHEET.",
        )
        parser.add_argument(
            "--sheet-id",
            dest="sheet_id",
            default=argparse.SUPPRESS,
            help="Google Sheet ID from .../spreadsheets/d/ID/... (overrides SheetConfig).",
        )
        parser.add_argument(
            "--sheet-range",
            dest="sheet_range",
            default=argparse.SUPPRESS,
            help="Range as in admin, e.g. N113:R121 or !B2:J50.",
        )
        parser.add_argument(
            "--tab",
            dest="tab_name",
            default=argparse.SUPPRESS,
            help='Tab name prefix before range. Empty tab: --tab ""',
        )
        parser.add_argument(
            "--touch-config",
            action="store_true",
            help="Update SheetConfig.last_synced_at (default off for historical imports).",
        )

    def handle(self, *args, **options):
        kind = options["kind"]
        code = options["code"]
        if code is None:
            code = "LIVEBOARD" if kind == "weekly" else "DISPATCHER_SHEET"

        kwargs = {
            "code": code,
            "year": options["year"],
            "iso_week": options["iso_week"],
            "touch_config_synced_at": options["touch_config"],
        }
        for key in ("sheet_id", "sheet_range", "tab_name"):
            if key in options:
                kwargs[key] = options[key]

        if kind == "weekly":
            ok = sync_weekly_sheet(**kwargs)
        else:
            ok = sync_dispatcher_sheet(**kwargs)

        if not ok:
            raise CommandError(
                "Import failed (missing SheetConfig and overrides?, empty API response, or bad range). "
                "Check Django logs."
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Done: kind=%s, ISO %s-W%02d." % (kind, options["year"], options["iso_week"])
            )
        )
