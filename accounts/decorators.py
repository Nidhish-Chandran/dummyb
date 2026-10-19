from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login


def _get_profile(user):
    return getattr(user, 'profile', None)


def _check_operational(request, profile):
    if not request.user.is_superuser and profile is not None:
        if not profile.is_operational:
            status_desc = profile.get_account_status_display().lower()
            reason = profile.suspension_reason or "Account suspended or pending administrative approval."
            raise PermissionDenied(f"Access Denied: Your account is {status_desc}. {reason}")


def authority_required(view_func):
    """
    Authority console access — Platform Administrators AND active Authority officers.
    Rangers are excluded — ranger access lives under /ranger/.
    Citizens receive HTTP 403.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        _check_operational(request, profile)

        if profile is not None and (profile.is_admin or profile.is_authority_officer):
            return view_func(request, *args, **kwargs)

        if profile is not None and profile.is_ranger:
            raise PermissionDenied(
                "Access Denied: Rangers must use the Ranger Console (/ranger/). "
                "The Authority dashboard is restricted to authority officers.")

        raise PermissionDenied("Access Denied: Authority officer privileges required to access GIS map and surveillance data.")

    return _wrapped_view


def citizen_required(view_func):
    """Citizen module access — any authenticated operational user that is not a ranger."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        _check_operational(request, profile)

        if profile is not None and profile.is_ranger:
            raise PermissionDenied(
                "Access Denied: Rangers must use the Ranger Console (/ranger/).")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def ranger_required(view_func):
    """Ranger Console access — only users whose effective role is RANGER and approved."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        _check_operational(request, profile)

        if profile is not None and profile.is_ranger:
            return view_func(request, *args, **kwargs)

        raise PermissionDenied("Access Denied: This area is restricted to registered Forest Rangers.")

    return _wrapped_view


def admin_required(view_func):
    """Platform administrator access only."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')

        profile = _get_profile(request.user)
        if request.user.is_superuser or (profile is not None and profile.is_admin):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    return _wrapped_view
