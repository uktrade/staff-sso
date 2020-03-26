import logging

from django.conf import settings
from django.http import HttpResponse
from django.urls import resolve
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

from sso.core.ip_filter import get_client_ip, is_valid_ip

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
                client_ip = get_client_ip(request)

                if not is_valid_ip(client_ip):
                    return HttpResponse('Unauthorized', status=401)

        return get_response(request)

    return middleware


class SessionCookieFixMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        if 'sessionid' in response.cookies:
            response.cookies['sessionid']['SameSite'] = 'None'

        return response
