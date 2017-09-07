from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin


class NeverCacheMiddleware(MiddlewareMixin):
    """Cache-Control: no-cache for all responses."""

    def process_response(self, request, response):
        """Set no-cache policy to response."""
        add_never_cache_headers(response)
        return response
