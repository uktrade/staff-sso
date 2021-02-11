from unittest import mock

from django.http import HttpResponse

from sso.core.middleware import NeverCacheMiddleware


class TestNeverCacheMiddleware:
    """Tests for NeverCacheMiddleware."""

    def test_no_cache_headers_added(self):
        """Test that the middleware adds a cache-control header with no-cache policy."""
        response = HttpResponse()

        middleware = NeverCacheMiddleware()
        middleware.process_response(request=mock.Mock(), response=response)

        assert (
            response["cache-control"]
            == "max-age=0, no-cache, no-store, must-revalidate, private"
        )
