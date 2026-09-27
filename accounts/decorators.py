from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login


def _get_profile(user):
    return getattr(user, 'profile', None)


def authority_required(view_func):
    """
    Platform Administrator ONLY (Authority console).

    Rangers are deliberately excluded — ranger access lives under /ranger/
    with its own dashboard, assignments and object-level security.
    Citizens receive HTTP 403; Rangers receive HTTP 403 pointing them to
    their own console.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        if profile is not None and profile.is_admin:
            return view_func(request, *args, **kwargs)

        if profile is not None and profile.is_ranger:
            raise PermissionDenied(
                "Access Denied: Rangers must use the Ranger Console (/ranger/). "
                "The Authority dashboard is restricted to platform administrators.")

        raise PermissionDenied("Access Denied: Higher Authority privileges required to access GIS map and surveillance data.")

    return _wrapped_view


def ranger_required(view_func):
    """Ranger Console access — only users whose effective role is RANGER."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        if profile is not None and profile.is_ranger:
            return view_func(request, *args, **kwargs)

        raise PermissionDenied("Access Denied: This area is restricted to registered Forest Rangers.")

    return _wrapped_view
