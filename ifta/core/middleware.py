"""Project middleware."""

from __future__ import annotations

import sys


class DevClearHstsMiddleware:
    """On runserver, clear browser HSTS cached from earlier production-like .env."""

    def __init__(self, get_response):
        self._active = "runserver" in sys.argv
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if self._active:
            response["Strict-Transport-Security"] = "max-age=0"
        return response
