import logging

from django.conf import settings
from django.http import HttpResponse
from django.urls import resolve
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class NeverCacheMiddleware(MiddlewareMixin):
    """Cache-Control: no-cache for all responses."""

    def process_response(self, request, response):
        """Set no-cache policy to response."""
        add_never_cache_headers(response)
        return response


def AdminIpRestrictionMiddleware(get_response):

    def middleware(request):
        if resolve(request.path).app_name == 'admin':
            if settings.RESTRICT_ADMIN:
                try:
                    remote_address = request.META['HTTP_X_FORWARDED_FOR'].split(',')[-2].strip()  # noqa: E501
                except (IndexError, KeyError):
                    logger.warning(
                        'X-Forwarded-For header is missing or does not '
                        'contain enough elements to determine the '
                        'client\'s ip')
                    return HttpResponse('Unauthorized', status=401)

                if remote_address not in settings.ALLOWED_ADMIN_IPS:
                    return HttpResponse('Unauthorized', status=401)

        return get_response(request)

    return middleware
