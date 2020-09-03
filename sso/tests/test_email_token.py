import datetime as dt
from unittest.mock import ANY

import pytest
from django.conf import settings
from django.utils import timezone
from freezegun import freeze_time

from sso.emailauth.forms import EmailForm
from sso.emailauth.models import EmailToken
from sso.emailauth.views import EmailAuthView, InvalidToken

from .factories.user import UserFactory

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

pytestmark = [
    pytest.mark.django_db
]


def _get_email_token_obj(email):
    assert EmailToken.objects.count() == 0

    EmailToken.objects.create_token(email)

    assert EmailToken.objects.count() == 1

    return EmailToken.objects.first()


class TestEmailTokenModel:
    def test_extract_name_from_email(self):
        test_emails = [
            ['aaa.bbb.ccc@example.com', 'Aaa', 'Bbb ccc'],
            ['aaa@example.com', 'Aaa', ''],
            ['aaa-bbb@example.com', 'Aaa-bbb', ''],
            ['aaa.bbb@example.com', 'Aaa', 'Bbb'],
            ['aaa.bbb-ccc@example.com', 'Aaa', 'Bbb-ccc']
        ]

        for email, first_name, last_name in test_emails:
            obj = EmailToken()
            obj.extract_name_from_email(email)
            assert obj.first_name == first_name, email
            assert obj.last_name == last_name, email

    def test_get_user_creates_user_with_name(self):
        token_obj = _get_email_token_obj('john.smith@testing.com')

        user = token_obj.get_user()

        assert user.first_name == 'John'
        assert user.last_name == 'Smith'
        assert user.is_active == True


class TestEmailTokenManager:
    def test_create_user_populates_name_field(self):

        token_obj = _get_email_token_obj('john.smith@testing.com')

        assert token_obj.first_name == 'John'
        assert token_obj.last_name == 'Smith'


class TestEmailTokenForm:
    def test_extract_redirect_uri(self):
        next_url = '/o/authorize/?scope=introspection&state=kalle&redirect_uri=https://localhost:5000/authorised&response_type=code&client_id=0j855NJvxO1R3Ld5qDVRsZ1WaGEbSqjxbYRFcRcw' # noqa

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == 'https://localhost:5000'

    def test_extract_redirect_uri_missing_next_url(self):

        next_url = ''

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == ''

    def test_extract_redirect_uri_missing_redirect_uri_qs(self):

        next_url = 'a-random-url?a=b&b=c&no_redirect_uri=False'

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == next_url

    def test_email_property(self):

        domain = settings.EMAIL_TOKEN_DOMAIN_WHITELIST[0]

        form = EmailForm({
            'username': 'test.user',
            'domain': domain

        })

        assert form.is_valid()

        assert form.cleaned_data['username'] == 'test.user'
        assert form.cleaned_data['domain'] == domain

        assert form.email == form.cleaned_data['username'] + form.cleaned_data['domain']

    def test_invalid_username_is_detected(self):
        domain = settings.EMAIL_TOKEN_DOMAIN_WHITELIST[0]

        form = EmailForm({
            'username': 'invalid@username.com',
            'domain': domain
        })

        assert not form.is_valid()


class TestEmailAuthView:
    def test_get_token_object_invalid_token(self):

        eav = EmailAuthView()
        with pytest.raises(InvalidToken):
            eav.get_token_object('non-existent-token-id')

    def test_get_token_object_expired_token(self):
        initial_datetime = dt.datetime.now()
        expired_datetime = initial_datetime + dt.timedelta(settings.EMAIL_TOKEN_TTL + 1)

        with freeze_time(initial_datetime) as frozen_time:

            token = EmailToken.objects.create_token('test@test.com')
            frozen_time.move_to(expired_datetime)

            eav = EmailAuthView()
            with pytest.raises(InvalidToken):
                eav.get_token_object(token)

    def test_invalid_token_get(self, client):

        token = 'aninvalidtoken'

        url = reverse('emailauth:email-auth-signin', kwargs=dict(token=token))

        response = client.get(url)

        template_names = map(lambda el: el.name, response.templates)

        assert response.status_code == 200
        assert 'emailauth/invalid-token.html' in template_names

    def test_invalid_token_post(self, client):

        token = 'aninvalidtoken'

        url = reverse('emailauth:email-auth-signin', kwargs=dict(token=token))

        response = client.post(url)

        template_names = map(lambda el: el.name, response.templates)

        assert response.status_code == 200
        assert 'emailauth/invalid-token.html' in template_names

    def test_expired_token(self, client):

        initial_datetime = dt.datetime.now()
        expired_datetime = initial_datetime + dt.timedelta(settings.EMAIL_TOKEN_TTL + 1)

        with freeze_time(initial_datetime) as frozen_time:

            token = EmailToken.objects.create_token('test@test.com')

            url = reverse('emailauth:email-auth-signin', kwargs=dict(token=token))

            frozen_time.move_to(expired_datetime)

            response = client.get(url)

            template_names = map(lambda el: el.name, response.templates)

            assert response.status_code == 200
            assert 'emailauth/invalid-token.html' in template_names

    def test_next_url(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        response = client.post(url)

        assert response.status_code == 302
        assert response.url == 'https://myapp.com'

    def test_user_is_authenticated(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.post(url)

        assert '_auth_user_id' in client.session

    def test_x_application_access_log_is_created(self, client, mocker):

        email = 'test@test.com'

        mock_create_x_access_log = mocker.patch('sso.emailauth.views.create_x_access_log')

        token = EmailToken.objects.create_token(email)

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.post(url)

        mock_create_x_access_log.assert_called_with(ANY, 200, message='Email Token Auth', email=email)

    def test_user_is_not_authenticated_and_token_is_not_invalidated_with_get_request(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.get(url)

        token = EmailToken.objects.get(token=token)

        assert '_auth_user_id' not in client.session
        assert not token.used

    def test_token_is_invalidated_with_post_request(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.post(url)

        token = EmailToken.objects.get(token=token)
        assert token.used

    def test_authentication_with_alternative_email(self, client):
        """Test user can authenticate with an alternative email"""

        user = UserFactory(email='test@test.com')
        user.emails.create(email='test@alternative.com')

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.post(url)

        assert '_auth_user_id' in client.session

    def test_email_saved_in_cookie(self, client):

        form_data = {
            'username': 'john.smith',
            'domain': '@digital.trade.gov.uk',
        }

        client.post(reverse('emailauth:email-auth-initiate'), form_data)

        assert client.cookies['sso_auth_email'].value == 'john.smith@digital.trade.gov.uk'

    def test_email_is_remembered(self, client):

        client.cookies['sso_auth_email'] = 'john.smith@digital.trade.gov.uk'

        response = client.get(reverse('emailauth:email-auth-initiate'))

        content = response.content.decode('utf-8')

        assert '<option value="@digital.trade.gov.uk" selected>' in content
        assert '<input type="text" name="username" value="john.smith"' in content

    def test_invalid_email_is_ignored(self, client):

        client.cookies['sso_auth_email'] = 'richard.jones@invalid-not-in-whitelist.gov.uk'

        response = client.get(reverse('emailauth:email-auth-initiate'))

        content = response.content.decode('utf-8')

        assert 'richard.jones' not in content
        assert '@invalid-not-in-whitelist.gov.uk' not in content

    @freeze_time('2019-08-29 15:50:00.000000+00:00')
    def test_last_login_time_recorded_against_email(self, client):

        user = UserFactory(email='test@test.com')
        user.emails.create(email='test@alternative.com')

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('emailauth:email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.post(url)

        assert user.emails.get(email='test@test.com').last_login == timezone.now()
