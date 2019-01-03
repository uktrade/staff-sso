import json
from unittest.mock import Mock, patch

import pytest

from googleapiclient.errors import HttpError

from sso.samlidp.management.commands.sync_with_google import http_retry


def build_google_http_error(status=403, reason='userRateLimitExceeded'):
    content = {
        'error': {
            'errors': [
                {
                    'domain': 'usageLimits',
                    'reason': reason,
                    'message': 'Rate limit exceeded.'
                }
            ],
            'code': status,
            'message': 'Rate limit exceeded.'
        }
    }

    response = Mock(status=status, content=json.dumps(content).encode('utf-8'))

    return HttpError(response, response.content)


class TestHttpRetry:
    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_non_http_error(self, _):
        func = Mock(side_effect=Exception('Uh oh'))

        func = http_retry()(func)

        with pytest.raises(Exception):
            func()

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_non_403(self, _):

        func = Mock(side_effect=build_google_http_error(status=503))
        orig_func = func
        func = http_retry()(func)

        with pytest.raises(HttpError):
            func()

        assert orig_func.call_count == 1

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_exceeds_max_attempts(self, _):

        exception = build_google_http_error(status=403, reason='userRateLimitExceeded')

        func = Mock(side_effect=exception)
        orig_func = func
        func = http_retry()(func)

        with pytest.raises(HttpError):
            func()

        assert orig_func.call_count == 5

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_retry_http_403_error(self, _):
        exception = build_google_http_error(status=403, reason='userRateLimitExceeded')

        func = Mock(side_effect=[exception, exception, 'testing123'])
        orig_func = func
        func = http_retry()(func)

        assert func() == 'testing123'

        assert orig_func.call_count == 3

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_retry_http_403_with_non_retrying_reason_is_not_retried(self, _):
        exception = build_google_http_error(status=403, reason='DONOTRETRY')

        func = Mock(side_effect=[exception, exception, 'testing123'])
        orig_func = func
        func = http_retry()(func)

        with pytest.raises(HttpError):
            func()

        assert orig_func.call_count == 1

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_succeeds(self, _):

        func = Mock(return_value='testing123')

        func = http_retry()(func)

        assert func() == 'testing123'
