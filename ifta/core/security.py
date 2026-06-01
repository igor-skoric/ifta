"""Shared security helpers (TV displays, client IP, tokens)."""

from __future__ import annotations

import ipaddress
import secrets
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from accounts.services import has_permission_for_user_context


def get_client_ip(request) -> str | None:
    """Resolve client IP; honor X-Forwarded-For only when explicitly trusted."""
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _ip_in_allowlist(ip_str: str | None) -> bool:
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for entry in getattr(settings, "STATISTICS_TV_ALLOWED_IPS", []):
        try:
            if "/" in entry:
                if ip in ipaddress.ip_network(entry, strict=False):
                    return True
            elif ip == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def _tv_token_from_request(request) -> str | None:
    expected = getattr(settings, "STATISTICS_TV_TOKEN", "") or ""
    if not expected:
        return None
    header = request.headers.get("X-Statistics-TV-Token", "")
    if header and secrets.compare_digest(header, expected):
        return expected
    query = request.GET.get(getattr(settings, "STATISTICS_TV_TOKEN_QUERY_PARAM", "tv_token"), "")
    if query and secrets.compare_digest(query, expected):
        return expected
    return None


def is_statistics_tv_client(request) -> bool:
    """
    Unauthenticated read access for wall displays:
    - STATISTICS_TV_PUBLIC_READ=True (explicit opt-in), or
    - client IP in STATISTICS_TV_ALLOWED_IPS, or
    - valid STATISTICS_TV_TOKEN (header or query param).
    """
    if getattr(settings, "STATISTICS_TV_PUBLIC_READ", False):
        return True
    if _ip_in_allowlist(get_client_ip(request)):
        return True
    if _tv_token_from_request(request) is not None:
        return True
    return False


def can_read_statistics(request) -> bool:
    if (
        getattr(request, "user", None)
        and request.user.is_authenticated
        and has_permission_for_user_context(request.user, "statistics.view")
    ):
        return True
    return is_statistics_tv_client(request)


def statistics_tv_or_permission_required(view_func):
    """TV wall pages / APIs: login+permission OR configured TV access."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if can_read_statistics(request):
            return view_func(request, *args, **kwargs)
        if getattr(request, "user", None) and request.user.is_authenticated:
            from django.contrib import messages

            messages.error(request, "You do not have permission for this page.")
            return redirect(settings.LOGIN_REDIRECT_URL)
        return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)

    return wrapper
