from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def verified_email_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.email_verified:
            messages.warning(
                request,
                "Verify your email address before using medicine listings or requests.",
            )
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapped
