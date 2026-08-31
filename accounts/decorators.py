from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login

def authority_required(view_func):
    """
    Decorator for views that checks if the logged-in user is a Higher Authority or Admin.
    If unauthenticated, redirects to login.
    If logged in as a Citizen, raises HTTP 403 PermissionDenied.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url='accounts:login')
        
        if hasattr(request.user, 'profile') and request.user.profile.is_authority:
            return view_func(request, *args, **kwargs)
            
        raise PermissionDenied("Access Denied: Higher Authority privileges required to access GIS map and surveillance data.")
        
    return _wrapped_view
