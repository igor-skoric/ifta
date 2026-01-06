import os
from django.apps import AppConfig
from django.conf import settings


class StatisticConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'statistic'

    def ready(self):
        # Sprečava duplo startovanje kod runserver autoreload-a
        if settings.DEBUG:
            if os.environ.get("RUN_MAIN") != "true":
                return

            # from .scheduler_dev import start
            # start()