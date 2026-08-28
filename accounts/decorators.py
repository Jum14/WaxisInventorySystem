from functools import wraps
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def get_role(user):
    profile = getattr(user, "profile", None)
    if profile:
        return profile.role
    return None

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            role = get_role(request.user)
            if role not in allowed_roles:
                return render(request, "403.html", status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator