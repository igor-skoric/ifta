from django.core.management.base import BaseCommand
from statistic.services.sync_sheet import (
    sync_weekly_driver_data,
    sync_weekly_sheet,
    sync_active_trucks_final
)


class Command(BaseCommand):
    help = "Run sheets sync once (for cron)."

    def handle(self, *args, **options):
        # Po želji: redom kako ti odgovara
        sync_weekly_driver_data()
        sync_weekly_sheet()
        sync_active_trucks_final()
        self.stdout.write(self.style.SUCCESS("Sync done."))
