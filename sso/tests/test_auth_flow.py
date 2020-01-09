import base64
import os
import re
from functools import lru_cache
from unittest.mock import Mock
from urllib.parse import parse_qs, quote, urlencode, urlsplit

import pytest
from django.http.cookie import SimpleCookie
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from freezegun import freeze_time

from sso.user.models import User

from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory


@lru_cache()
def get_saml_response(action='login'):
    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data',
        f'saml_{action}_response.xml'
    )
    with open(file_path, 'rb') as f:
        return f.read()


SAML_SSO_SERVICE = 'http://localhost:8080/simplesaml/saml2/idp/SSOService.php'
SAML_LOGOUT_SERVICE = 'http://localhost:8080/simplesaml/saml2/idp/SingleLogoutService.php'
SAML_METADATA_URL = 'http://localhost:8080/simplesaml/saml2/idp/metadata.php'

SAML_LOGIN_URL = reverse_lazy('saml2_login')
SAML_LOGOUT_URL = reverse_lazy('saml2_logout')
SAML_ACS_URL = reverse_lazy('saml2_acs')
SAML_LS_POST_URL = reverse_lazy('saml2_ls_post')  # for logout

OAUTH_AUTHORIZE_URL = reverse_lazy('oauth2_provider:authorize')
OAUTH_REDIRECT_URL = 'http://localhost/authorized'
OAUTH_TOKEN_URL = reverse_lazy('oauth2_provider:token')

SAML_LOGIN_START_URL = reverse_lazy('saml2_login_start')


pytestmark = [
    pytest.mark.django_db
]


def create_oauth_application(users=None):
    """
    Create an oauth application and returns a tuple
    (
        application instance,
        oauth params as dict for the authorize request
    )
    """
    application = ApplicationFactory(
        redirect_uris=OAUTH_REDIRECT_URL,
        users=users
    )

    oauth_params = {
        'scope': 'read write',
        'response_type': 'code',
        'client_id': application.client_id
    }
    return application, oauth_params


def log_user_in(client):
    user = UserFactory(email='user1@example.com')
    session_info = {
        'ava': {
            'email': ['user1@example.com']
        },
        'name_id': Mock(text='user1@example.com'),
        'came_from': '/accounts/profile/',
        'issuer': SAML_SSO_SERVICE,
    }
    logged_in = client.login(
        session_info=session_info,
        attribute_mapping={'email': ('email',)}
    )
    assert logged_in
    return user


class TestOAuthAuthorize:
    def test_redirects_to_saml_login(self, client):
        """
        Test that calling authorize redirects to the SAML login page
        if the user is not authenticated.
        """
        application, authorize_params = create_oauth_application()
        response = client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        assert response.status_code == 302
        assert response.url.startswith(
            f'{SAML_LOGIN_START_URL}?next={OAUTH_AUTHORIZE_URL}'
        )

    def test_x_application_log_is_created(self, client, mocker):
        user = UserFactory()
        application, authorize_params = create_oauth_application(users=[user])

        mock_create_x_access_log = mocker.patch('sso.oauth2.views.create_x_access_log')

        client.force_login(user)

        client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        assert mock_create_x_access_log.called
        request = mock_create_x_access_log.mock_calls[0][1][0]
        mock_create_x_access_log.assert_called_once_with(
            request, 200,
            oauth2_application=application.name)

    def test_x_application_log_is_created_on_access_denied(self, client, mocker):
        user = UserFactory()
        application, authorize_params = create_oauth_application()

        mock_create_x_access_log = mocker.patch('sso.oauth2.views.create_x_access_log')

        client.force_login(user)

        client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        assert mock_create_x_access_log.called
        request = mock_create_x_access_log.mock_calls[0][1][0]
        mock_create_x_access_log.assert_called_once_with(
            request, 403,
            oauth2_application=application.name)


class TestSAMLLogin:
    def test_valid_saml_login_form(self, client, settings):
        """
        Test that the saml login form includes the appropriate hidden values.
        """
        application, authorize_params = create_oauth_application()

        login_url = f'{SAML_LOGIN_URL}?next={OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        response = client.get(login_url)

        # check form
        content = response.content.decode('utf-8')
        assert response.status_code == 200
        assert f'<form method="post" action="{SAML_SSO_SERVICE}" name="SSO_Login">' in content
        assert '<input type="hidden" name="SAMLRequest"' in content
        assert f'<input type="hidden" name="RelayState" value="{OAUTH_AUTHORIZE_URL}?scope=read write" />' in content
        assert '<input type="submit" value="Log in" />' in content

        # check saml request
        saml_request_search = re.search('<input type="hidden" name="SAMLRequest" value="(.*)" />', content)
        saml_request = base64.b64decode(saml_request_search.group(1)).decode('utf-8')

        assert '<ns2:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>' in saml_request
        assert f'Destination="{SAML_SSO_SERVICE}"' in saml_request
        assert f'AssertionConsumerServiceURL="{settings.SAML_ACS_URL}"' in saml_request

    def test_post_binding_form_sanitises_form_fields(self, client):
        """
        Test that the RelayState field is correctly sanitised
        """
        application, authorize_params = create_oauth_application()

        malicious_code = '%22%3E%3Cscript%3Ealert%28%27NCC%2BXSS%27%29%3C%2Fscript%3E'

        login_url = f'{SAML_LOGIN_URL}?next={OAUTH_AUTHORIZE_URL}{malicious_code}?{urlencode(authorize_params)}'
        response = client.get(login_url)

        # check form
        content = response.content.decode('utf-8')
        assert response.status_code == 200
        assert '<input type="hidden" name="RelayState" value="/o/authorize/&quot;&gt;&lt;script&gt;alert(&#39;NCC+XSS&#39;)&lt;/script&gt;?scope=read write" />' in content  # noqa
        assert '<script>alert(\'NCC+XSS\')</script>' not in content

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_generates_oauth_code(self, client, mocker):
        """
        Test that after successfully logging into the IdP, the app redirects to the oauth authorize url
        which generates the auth code.
        """

        # we require an existing user with permissions to access the application
        user = UserFactory(email='user1@example.com')

        application, authorize_params = create_oauth_application(users=[user])
        response = client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        assert User.objects.count() == 1

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        # check saml login
        assert response.status_code == 302
        authorize_url = response['location']
        assert authorize_url == data['RelayState']

        # check user in db
        assert User.objects.count() == 1
        user = User.objects.first()
        assert user.email == 'user1@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'

        # check token
        response = client.get(authorize_url)
        assert response.status_code == 302

        authorize_qs = parse_qs(response['location'].split('?')[1])
        assert 'code' in authorize_qs

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_x_application_saml_log_message(self, client, mocker):
        """
        Test that an x-application log message is created
        """

        # we require an existing user with permissions to access the application
        user = UserFactory(email='user1@example.com')

        application, authorize_params = create_oauth_application(users=[user])
        client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        mock_create_x_access_log = mocker.patch('sso.samlauth.views.create_x_access_log')

        client.post(SAML_ACS_URL, data)

        assert mock_create_x_access_log.called
        request = mock_create_x_access_log.mock_calls[0][1][0]
        mock_create_x_access_log.assert_called_once_with(
            request, 200,
            entity_id='http://localhost:8080/simplesaml/saml2/idp/metadata.php',
            message='Remote IdP Auth',
            email='user1@example.com')

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_using_name_id(self, client, mocker, settings):
        """
        Test that `settings.SAML_IDPS_USE_NAME_ID_AS_USERNAME` works correctly, and that the `User.email` field is not
        overridden by the attribute mapping
        """

        settings.SAML_IDPS_USE_NAME_ID_AS_USERNAME = ['http://localhost:8080/simplesaml/saml2/idp/metadata.php']

        application, authorize_params = create_oauth_application()
        response = client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        # check saml login
        assert response.status_code == 302
        authorize_url = response['location']
        assert authorize_url == data['RelayState']

        # check user in db
        assert User.objects.count() == 1
        user = User.objects.first()
        assert user.email == 'user1(nameid)@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_without_permissions_results_in_access_denied(self, client, mocker):
        """
        Test that after successfully logging into the IdP, the app redirects to the oauth authorize url
        which generates the auth code.
        """
        application, authorize_params = create_oauth_application()
        response = client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        assert User.objects.count() == 0

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        # check saml login
        assert response.status_code == 302
        authorize_url = response['location']
        assert authorize_url == data['RelayState']

        # check user in db
        assert User.objects.count() == 1
        user = User.objects.first()
        assert user.email == 'user1@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'

        # check token
        response = client.get(authorize_url)
        assert response.status_code == 302

        assert response['location'] == '/access-denied/'

        # The application the user tried to access is recorded in session under the _last_failed_access_app
        # and is used by the request access form.
        assert client.session['_last_failed_access_app'] == application.name

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_with_alternative_email(self, client, mocker):
        """
         Test that after successfully logging into the IdP, the app redirects to the oauth authorize url
         which generates the auth code.
         """

        user = UserFactory(email='hello@testing.com', email_list=['user1@example.com', 'test@bbb.com', 'test@ccc.com'])

        application, authorize_params = create_oauth_application(users=[user])
        response = client.get(OAUTH_AUTHORIZE_URL, data=authorize_params)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        assert User.objects.count() == 1

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        # check saml login
        assert response.status_code == 302
        authorize_url = response['location']
        assert authorize_url == data['RelayState']

        # check user in db
        assert User.objects.count() == 1
        user = User.objects.first()
        assert user.emails.filter(email='user1@example.com').exists()

        # check token
        response = client.get(authorize_url)
        assert response.status_code == 302

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_with_default_redirect_url(self, client, mocker):
        """
        Test that if no redirect url is specified, it redirects to the default
        saml2_logged_in view.
        """
        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
        }

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)
        assert response.status_code == 302
        assert response['location'] == reverse('saml2_logged_in')

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_fails_if_signature_invalid(self, client, mocker):
        """
        Test that if the saml signature is invalid, the login fails.
        """

        application, authorize_params = create_oauth_application()

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        MockOutstandingQueriesCache = mocker.patch('djangosaml2.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = False

        assert client.post(SAML_ACS_URL, data).status_code == 403


class TestOAuthToken:
    def _obtain_auth_code(self, client, authorize_params):
        authorize_url = f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'

        response = client.get(authorize_url)
        assert response.status_code == 302

        authorize_qs = parse_qs(response['location'].split('?')[1])
        assert 'code' in authorize_qs
        return authorize_qs['code']

    def test_obtain_oauth_token(self, client):
        """
        Test that a valid oauth token can be obtained from a valid auth code.
        """
        user = log_user_in(client)
        application, authorize_params = create_oauth_application(users=[user])

        auth_code = self._obtain_auth_code(client, authorize_params)

        # exchange for token
        response = client.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'redirect_uri': OAUTH_REDIRECT_URL,
            }
        )

        assert response.status_code == 200
        content = response.json()
        assert 'access_token' in content
        assert 'refresh_token' in content

    def test_obtain_oauth_token_fails_if_auth_code_invalid(self, client):
        """
        Test that without a valid auth code you cannot obtain an oauth token.
        """
        user = log_user_in(client)
        application, authorize_params = create_oauth_application(users=[user])

        self._obtain_auth_code(client, authorize_params)

        # exchange for token
        response = client.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': 'invalid',
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'redirect_uri': OAUTH_REDIRECT_URL,
            }
        )

        assert response.status_code == 401
        assert response.json() == {
            'error': 'invalid_grant'
        }

    def test_obtain_oauth_token_fails_if_client_id_invalid(self, client):
        """
        Test that without a valid client_id you cannot obtain an oauth token.
        """
        user = log_user_in(client)
        application, authorize_params = create_oauth_application(users=[user])

        auth_code = self._obtain_auth_code(client, authorize_params)

        # exchange for token
        response = client.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': 'invalid',
                'client_secret': application.client_secret,
                'redirect_uri': OAUTH_REDIRECT_URL,
            }
        )

        assert response.status_code == 401
        assert response.json() == {
            'error': 'invalid_client'
        }

    def test_obtain_oauth_token_fails_if_client_secret_invalid(self, client):
        """
        Test that without a valid client_secret you cannot obtain an oauth token.
        """
        user = log_user_in(client)
        application, authorize_params = create_oauth_application(users=[user])

        auth_code = self._obtain_auth_code(client, authorize_params)

        # exchange for token
        response = client.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': application.client_id,
                'client_secret': 'invalid',
                'redirect_uri': OAUTH_REDIRECT_URL,
            }
        )

        assert response.status_code == 401
        assert response.json() == {
            'error': 'invalid_client'
        }


class TestSAMLLogout:
    def test_valid_saml_logout_form(self, client, settings):
        """
        Test that the saml logout form includes the appropriate hidden values.
        """
        log_user_in(client)

        session_id = '_e257887eff90fde0f9ebda09c2d0825683969096d5'
        subject_id = '1={entity_id},2={name_id_format},4={ref}'.format(
            entity_id=quote(settings.SAML_CONFIG['entityid']),
            name_id_format=quote(settings.SAML_CONFIG['service']['sp']['name_id_format']),
            ref='c1e915bbc0586c0483a8f5654ed25d7afcdc315f'
        )

        s = client.session
        s['_saml2_identities'] = {
            subject_id: {
                SAML_METADATA_URL: [
                    None,
                    {
                        'session_index': session_id
                    }
                ]
            }
        }
        s['_saml2_subject_id'] = subject_id
        s.save()

        response = client.get(SAML_LOGOUT_URL)

        # check form
        content = response.content.decode('utf-8')
        assert response.status_code == 200
        assert f'<form action="{SAML_LOGOUT_SERVICE}" method="post">' in content
        assert '<input type="hidden" name="SAMLRequest"' in content
        assert '<input type="hidden" name="RelayState"' in content
        assert '<input type="submit" value="Continue"/>' in content

        # check saml request
        saml_request_search = re.search('<input type="hidden" name="SAMLRequest" value="(.*)"/>', content)
        saml_request = base64.b64decode(saml_request_search.group(1)).decode('utf-8')

        assert '<ns2:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>' in saml_request
        assert f'Destination="{SAML_LOGOUT_SERVICE}"' in saml_request
        assert f'<ns0:SessionIndex>{session_id}</ns0:SessionIndex>' in saml_request

    @freeze_time('2017-06-30 16:24:00.000000+00:00')
    def test_saml_logout_with_default_redirect_url(self, client, mocker):
        """
        Test that if no redirect url is specified, it redirects to the default
        saml2_logged_out view.
        """
        log_user_in(client)

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='logout'))],
        }

        assert dict(client.session) != {}

        response = client.post(SAML_LS_POST_URL, data)

        assert response.status_code == 302
        assert response['location'] == reverse('saml2_logged_out')
        assert dict(client.session) == {}

    def test_logged_out_result_view_redirects_if_user_logged_in(self, client):
        """
        If the user is logged in, the 'logged out' default result view redirects
        to the default result 'logged in' view.
        """
        log_user_in(client)

        response = client.get(reverse('saml2_logged_out'))
        assert response.status_code == 302
        assert response['location'] == reverse('saml2_logged_in')


class TestSessionLogout:
    """
    Whilst the saml2 logout is broken due to Core's logout url not killing the ADFS session we're
    using an alternative logout view that destroys the session
    """
    def test_logout_removes_all_keys(self, client):

        log_user_in(client)

        assert '_auth_user_id' in client.session
        client.session['_saml2_stuff'] = dict(saml='stuff')

        client.get(reverse('localauth:session-logout'))

        assert list(client.session.keys()) == []

    def test_logout_redirects_to_logged_out_url(self, client, settings):
        log_user_in(client)

        response = client.get(reverse('localauth:session-logout'))
        assert response.status_code == 302
        assert response.url == settings.LOGOUT_REDIRECT_URL


class TestReAuth:
    def test_login_cookie_not_set_results_in_wayf_template(self, client, settings):
        settings.SAML_CONFIG['metadata']['local'] += [os.path.join(settings.SAML_CONFIG_DIR, 'idp_metadata_2.xml')]
        login_url = f'{SAML_LOGIN_URL}'
        response = client.get(login_url)

        assert response.status_code == 200
        assert response.templates[0].name == 'djangosaml2/wayf.html'

    def test_login_cookie_set_to_incorrect_value_results_in_wayf_template(self, client, settings):
        client.cookies.load({'last_login_idp': 'invalid-idp-entity-id'})
        settings.SAML_CONFIG['metadata']['local'] += [os.path.join(settings.SAML_CONFIG_DIR, 'idp_metadata_2.xml')]
        login_url = f'{SAML_LOGIN_URL}'
        response = client.get(login_url)

        assert response.status_code == 200
        assert response.templates[0].name == 'djangosaml2/wayf.html'

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_last_login_time_recorded_against_email(self, client, mocker):

        application, authorize_params = create_oauth_application()

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        assert response.status_code == 302

        assert User.objects.count() == 1
        user = User.objects.first()

        assert user.emails.count() == 1
        assert user.emails.first().last_login == timezone.now()

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_used_email_is_saved_in_cookie(self, client, mocker):
        application, authorize_params = create_oauth_application()

        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
            'RelayState': f'{OAUTH_AUTHORIZE_URL}?{urlencode(authorize_params)}'
        }

        MockOutstandingQueriesCache = mocker.patch('sso.samlauth.views.OutstandingQueriesCache')
        MockOutstandingQueriesCache().outstanding_queries.return_value = {'id-WmZMklyFygoDg96gy': 'test'}

        MockCryptoBackendXmlSec1 = mocker.patch('saml2.sigver.CryptoBackendXmlSec1', spec=True)
        MockCryptoBackendXmlSec1().validate_signature.return_value = True

        response = client.post(SAML_ACS_URL, data)

        assert response.status_code == 302
        assert client.cookies['sso_auth_email'].value == 'user1@example.com'


class TestEmailBasedAuthFlow:
    def test_invalid_email_leads_to_form_error(self, client):

        response = client.post(reverse('saml2_login_start'), {'email': 'test@invalid.com'})

        assert response.status_code == 200

        assert 'You can\'t use this email address to access DIT\'s internal services.'.encode('utf-8') in response.content

    def test_previously_used_email_is_rendered_on_form(self, client):
        client.cookies = SimpleCookie({'sso_auth_email': 'test@test.com'})

        response = client.get(reverse('saml2_login_start'))

        assert '<input type="text" name="email" value="test@test.com"'.encode('utf-8') in response.content

    def test_email_token_based_email_redirects_to_email_flow(self, client, settings):
        settings.EMAIL_TOKEN_DOMAIN_WHITELIST = ['@test.com']

        response = client.post(reverse('saml2_login_start'), {'email': 'test@test.com'})

        assert response.status_code == 302

        assert response.url == reverse('emailauth:email-auth-initiate-success')

    def test_redirect_to_idp(self, settings, client):

        settings.AUTH_EMAIL_TO_IPD_MAP={'a-test': ['@test.com']}
        response = client.post(reverse('saml2_login_start'), {'email': 'test@test.com'})

        assert response.status_code == 302
        assert response.url == '/saml2/login/?idp=http%3A//localhost%3A8080/simplesaml/saml2/idp/metadata.php'

    def test_querystring_is_preserved_on_redirect(self, settings, client):
        settings.AUTH_EMAIL_TO_IPD_MAP={'a-test': ['@test.com']}
        response = client.post(reverse('saml2_login_start') + '?a=hello&b=world', {'email': 'test@test.com'})

        qs_items = dict(parse_qs(urlsplit(response.url).query))

        assert response.status_code == 302
        assert len(qs_items.items()) == 3
        assert qs_items == {
            'idp': ['http://localhost:8080/simplesaml/saml2/idp/metadata.php'],
            'a': ['hello'],
            'b': ['world'],
        }

    def test_next_querystring_is_retained(self, client):

        response = client.post(reverse('saml2_login_start') + '?next=http://whatever', {'email': 'bad@invalid.com'})

        assert '<a href="/saml2/login/?next=http://whatever">Sign in using a different method</a>' in \
               response.content.decode('utf-8')
