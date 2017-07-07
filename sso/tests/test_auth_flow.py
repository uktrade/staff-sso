import base64
import os
import re
from functools import lru_cache
from urllib.parse import parse_qs, quote, urlencode

import pytest
from django.conf import settings
from django.urls import reverse, reverse_lazy
from freezegun import freeze_time
from saml2.sigver import SignatureError

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


pytestmark = [
    pytest.mark.django_db
]


def create_oauth_application():
    """
    Create an oauth application and returns a tuple
    (
        application instance,
        oauth params as dict for the authorize request
    )
    """
    application = ApplicationFactory(
        redirect_uris=OAUTH_REDIRECT_URL
    )

    oauth_params = {
        'scope': 'read write',
        'response_type': 'code',
        'client_id': application.client_id
    }
    return application, oauth_params


def log_user_in(client):
    UserFactory(email='user1@example.com')
    session_info = {
        'ava': {
            'email': ['user1@example.com']
        },
        'name_id': 'NameId',
        'came_from': '/accounts/profile/',
        'issuer': SAML_SSO_SERVICE,
    }
    logged_in = client.login(
        session_info=session_info,
        attribute_mapping={'email': ('email',)}
    )
    assert logged_in


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
            f'{SAML_LOGIN_URL}?next={OAUTH_AUTHORIZE_URL}'
        )


class TestSAMLLogin:
    def test_valid_saml_login_form(self, client):
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

        assert '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>' in saml_request
        assert f'Destination="{SAML_SSO_SERVICE}"' in saml_request
        assert f'AssertionConsumerServiceURL="{settings.SAML_ACS_URL}"' in saml_request

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_saml_login_generates_oauth_code(self, client, mocker):
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

        MockOutstandingQueriesCache = mocker.patch('djangosaml2.views.OutstandingQueriesCache')
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
    def test_saml_login_with_default_redirect_url(self, client, mocker):
        """
        Test that if no redirect url is specified, it redirects to the default
        saml2_logged_in view.
        """
        data = {
            'SAMLResponse': [base64.b64encode(get_saml_response(action='login'))],
        }

        MockOutstandingQueriesCache = mocker.patch('djangosaml2.views.OutstandingQueriesCache')
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

        with pytest.raises(SignatureError):
            client.post(SAML_ACS_URL, data)


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
        application, authorize_params = create_oauth_application()

        log_user_in(client)
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
        application, authorize_params = create_oauth_application()

        log_user_in(client)
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
        application, authorize_params = create_oauth_application()

        log_user_in(client)
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
        application, authorize_params = create_oauth_application()

        log_user_in(client)
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
    def test_valid_saml_logout_form(self, client):
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
        assert f'<form method="post" action="{SAML_LOGOUT_SERVICE}">' in content
        assert '<input type="hidden" name="SAMLRequest"' in content
        assert '<input type="hidden" name="RelayState"' in content
        assert '<input type="submit" value="Submit" />' in content

        # check saml request
        saml_request_search = re.search('<input type="hidden" name="SAMLRequest" value="(.*)" />', content)
        saml_request = base64.b64decode(saml_request_search.group(1)).decode('utf-8')

        assert '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>' in saml_request
        assert f'Destination="{SAML_LOGOUT_SERVICE}"' in saml_request
        assert f'<samlp:SessionIndex>{session_id}</samlp:SessionIndex>' in saml_request

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
