"""
Legacy Passenger path: ifta/wsgi.py

Re-uses core.wsgi.application (single django.setup — no imp.load_source).
"""

from core.wsgi import application

__all__ = ["application"]
