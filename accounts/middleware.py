from django.utils.cache import add_never_cache_headers
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect


class AuthenticatedNoCacheMiddleware:
    """
    1. Ensures authenticated HTML and JSON responses carry no-cache/no-store headers.
    2. Enforces active/operational account status on every request. If an account
       has been suspended or banned, terminates session immediately with explanation.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check account status if not superuser
            if not request.user.is_superuser:
                profile = getattr(request.user, 'profile', None)
                if profile and not profile.is_operational:
                    reason = profile.suspension_reason or "Account suspended by administrator."
                    status_name = profile.get_account_status_display()
                    logout(request)
                    if hasattr(request, '_messages'):
                        messages.error(
                            request,
                            f"Your session has been terminated because your account has been {status_name.lower()}. Reason: {reason}"
                        )
                    return redirect('accounts:login')

        response = self.get_response(request)
        if hasattr(request, 'user') and request.user.is_authenticated:
            content_type = response.get('Content-Type', '')
            if 'text/html' in content_type or 'application/json' in content_type:
                add_never_cache_headers(response)
        return response
