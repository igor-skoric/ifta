from django.core.management.base import BaseCommand
from statistic.services.sync_sheet import (
    sync_weekly_sheet,
    sync_dispatcher_sheet
)


class Command(BaseCommand):
    help = "Run sheet sync for sample_table screen."

    def handle(self, *args, **options):
        # sample_table koristi dispatchers i weekly statistic
        sync_dispatcher_sheet()
        sync_weekly_sheet()
        self.stdout.write(self.style.SUCCESS("Sync done."))
