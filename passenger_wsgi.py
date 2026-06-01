"""
cPanel / Passenger WSGI entry.

Application root on server: /home/labvit/IFTA
Django project package:     /home/labvit/IFTA/ifta  (contains manage.py, core/, …)

Do not use imp.load_source — it can call django.setup() twice (populate isn't reentrant).
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT, "ifta")

if os.path.isdir(PROJECT_DIR):
    sys.path.insert(0, PROJECT_DIR)
else:
    # Layout where manage.py lives directly in ROOT
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
