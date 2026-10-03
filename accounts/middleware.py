from django.utils.cache import add_never_cache_headers


class AuthenticatedNoCacheMiddleware:
    """
    Ensures authenticated HTML and JSON responses carry no-cache/no-store headers.
    This prevents back-button cache exposure of protected pages after logout,
    while leaving static files and public pages cached normally.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(request, 'user') and request.user.is_authenticated:
            content_type = response.get('Content-Type', '')
            if 'text/html' in content_type or 'application/json' in content_type:
                add_never_cache_headers(response)
        return response
