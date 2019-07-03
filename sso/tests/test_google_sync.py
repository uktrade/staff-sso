import json
from unittest.mock import Mock, patch

import pytest

from googleapiclient.errors import HttpError

from sso.samlidp.models import SamlApplication
from sso.samlidp.management.commands.sync_with_google import Command, http_retry
from sso.tests.factories.user import AccessProfileFactory, UserFactory


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


def _build_google_create_user_dict(**kwargs):
    data = {
        'primaryEmail': 'test.user@data.test.com',
        'id': 'fake-id',
        'suspended': False,
        'processed': False,
        'isAdmin': False
    }

    data.update(kwargs)

    return data


def _configure_google_user_mock(mock_service, users=None):
    """
    Configure the mock so that mock.users().list().execute() returns the users arg
    """
    mock_service.return_value.users.return_value.list.return_value.execute.return_value = {
        'users': users or [],
        'nextPageToken': '',
    }


class TestManagementCommand:
    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_without_access_and_not_in_google_is_not_syncd(self, mock_service, settings):
        saml_app = SamlApplication.objects.create(name='test', slug='sync-me')
        AccessProfileFactory(slug='an-mi-user', saml_apps_list=[saml_app])

        UserFactory(email='test.user@whatever.com')

        settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = 'sync-me'
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service)

        Command().handle()

        assert not [call for call in mock_service.mock_calls if call[0] == '().users().inserts']
        assert not [call for call in mock_service.mock_calls if call[0] == '().users().update']

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_without_access_and_in_google_is_disabled(self, mock_service, settings):
        saml_app = SamlApplication.objects.create(name='test', slug='sync-me')
        AccessProfileFactory(slug='an-mi-user', saml_apps_list=[saml_app])

        settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = 'sync-me'
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service, [_build_google_create_user_dict(suspended=True)])

        Command().handle(inactive_account_action='disable')

        assert not [call for call in mock_service.mock_calls if call[0] == '().users().inserts']
        updates = [call for call in mock_service.mock_calls if call[0] == '().users().update']
        assert len(updates) == 1
        assert updates[0][2]['userKey'] == 'fake-id'
        assert updates[0][2]['body']['suspended'] == 'true'

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_with_access_profile_not_in_google_is_created(self, mock_service, settings):

        saml_app = SamlApplication.objects.create(name='test', slug='sync-me')
        access_profile = AccessProfileFactory(slug='an-mi-user', saml_apps_list=[saml_app])

        user = UserFactory(email='test.user@whatever.com', add_access_profiles=[access_profile])

        settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = 'sync-me'
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service)

        Command().handle()

        inserts = [call for call in mock_service.mock_calls if call[0] == '().users().insert']

        expected_call_args = {
            'primaryEmail': '{}@{}'.format(user.email.split('@')[0], settings.MI_GOOGLE_EMAIL_DOMAIN),
            'name': {'givenName': user.first_name, 'familyName': user.last_name, 'fullName': user.get_full_name()},
            'hashFunction': 'SHA-1',
            'suspended': False
        }

        assert len(inserts) == 1
        for key, value in expected_call_args.items():
            assert inserts[0][2]['body'][key] == value

        assert len(inserts[0][2]['body']['password']) == 40

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_with_missing_name_is_created(self, mock_service, settings):

        saml_app = SamlApplication.objects.create(name='test', slug='sync-me')
        access_profile = AccessProfileFactory(slug='an-mi-user', saml_apps_list=[saml_app])
        user = UserFactory(email='test.user@whatever.com', add_access_profiles=[access_profile],
                           first_name='', last_name='')

        settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = 'sync-me'
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service)

        Command().handle()

        inserts = [call for call in mock_service.mock_calls if call[0] == '().users().insert']

        expected_call_args = {
            'primaryEmail': '{}@{}'.format(user.email.split('@')[0], settings.MI_GOOGLE_EMAIL_DOMAIN),
            'name': {'givenName': 'unspecified', 'familyName': 'unspecified', 'fullName': user.email},
            'hashFunction': 'SHA-1',
            'suspended': False
        }

        assert len(inserts) == 1
        for key, value in expected_call_args.items():
            assert inserts[0][2]['body'][key] == value

        assert len(inserts[0][2]['body']['password']) == 40

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_with_access_profile_but_disabled_in_google_is_reenabled(self, mock_service, settings):

        saml_app = SamlApplication.objects.create(name='test', slug='sync-me')
        access_profile = AccessProfileFactory(slug='an-mi-user', saml_apps_list=[saml_app])
        UserFactory(email='test.user@whatever.com', add_access_profiles=[access_profile])

        settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = 'sync-me'
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service, [_build_google_create_user_dict(suspended=True)])

        Command().handle()

        assert not [call for call in mock_service.mock_calls if call[0] == '().users().inserts']
        updates = [call for call in mock_service.mock_calls if call[0] == '().users().update']
        assert len(updates) == 1

        assert updates[0][2]['userKey'] == 'fake-id'
        assert updates[0][2]['body']['suspended'] == 'false'

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_google_admin_user_is_not_disabled(self, mock_service, settings):

        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service, [_build_google_create_user_dict(isAdmin=True)])

        Command().handle(inactive_account_action='disable')

        assert not [call for call in mock_service.mock_calls if call[0] == '().users().inserts']
        assert not [call for call in mock_service.mock_calls if call[0] == '().users().update']

    @pytest.mark.django_db
    @patch('sso.samlidp.management.commands.sync_with_google.get_google_client')
    def test_user_without_access_is_deleted(self, mock_service, settings):

        settings.MI_GOOGLE_EMAIL_DOMAIN = 'data.test.com'

        _configure_google_user_mock(mock_service, [_build_google_create_user_dict(suspended=True)])

        Command().handle(inactive_account_action='delete')

        assert not [call for call in mock_service.mock_calls if call[0] == '().users().inserts']
        assert not [call for call in mock_service.mock_calls if call[0] == '().users().update']
        deletes = [call for call in mock_service.mock_calls if call[0] == '().users().delete']
        assert len(deletes) == 1
        assert deletes[0][2]['userKey'] == 'fake-id'
