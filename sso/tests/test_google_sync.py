from unittest.mock import Mock, patch

import pytest

from googleapiclient.errors import HttpError

from sso.samlidp.management.commands.sync_with_google import http_retry


class TestHttpRetry:
    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_non_http_error(self, _):
        func = Mock(side_effect=Exception('Uh oh'))

        func = http_retry()(func)

        with pytest.raises(Exception):
            func()

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_non_403(self, _):
        response = Mock(status=503)

        func = Mock(side_effect=HttpError(response, b'content'))
        orig_func = func
        func = http_retry()(func)

        with pytest.raises(HttpError):
            func()

        assert orig_func.call_count == 1

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_exceeds_max_attempts(self, _):
        response = Mock(status=403)

        func = Mock(side_effect=HttpError(response, b'content'))
        orig_func = func
        func = http_retry()(func)

        with pytest.raises(HttpError):
            func()

        assert orig_func.call_count == 5

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_retry_http_403_error(self, _):
        response = Mock(status=403)

        func = Mock(side_effect=[HttpError(response, b'content'), HttpError(response, b'content'), 'testing123'])
        orig_func = func
        func = http_retry()(func)

        assert func() == 'testing123'

        assert orig_func.call_count == 3

    @patch('sso.samlidp.management.commands.sync_with_google.time.sleep')
    def test_http_error_succeeds(self, _):

        func = Mock(return_value='testing123')

        func = http_retry()(func)

        assert func() == 'testing123'
