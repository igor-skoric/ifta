from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .services import has_permission_for_user_context


def permission_required(permission_code):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_permission_for_user_context(request.user, permission_code):
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission for this page.")
            return redirect(settings.LOGIN_REDIRECT_URL)

        return wrapper

    return decorator

