import datetime as dt

import pytest
from django.conf import settings
from django.core.urlresolvers import reverse
from freezegun import freeze_time

from sso.emailauth.forms import EmailForm
from sso.emailauth.models import EmailToken

from .factories.user import UserFactory

pytestmark = [
    pytest.mark.django_db
]


class TestEmailTokenModel:
    def test_extract_name_from_email(self):
        test_emails = [
            ['aaa.bbb.ccc@example.com', 'aaa', 'bbb ccc'],
            ['aaa@example.com', 'aaa', ''],
            ['aaa-bbb@example.com', 'aaa-bbb', ''],
            ['aaa.bbb@example.com', 'aaa', 'bbb']
        ]

        for email, first_name, last_name in test_emails:
            obj = EmailToken()
            obj.extract_name_from_email(email)
            assert obj.first_name == first_name, email
            assert obj.last_name == last_name, email


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

        domain = settings.EMAIL_TOKEN_DOMAIN_WHITELIST[0][0]

        form = EmailForm({
            'username': 'test.user',
            'domain': domain

        })

        assert form.is_valid()

        assert form.cleaned_data['username'] == 'test.user'
        assert form.cleaned_data['domain'] == domain

        assert form.email == form.cleaned_data['username'] + form.cleaned_data['domain']

    def test_invalid_username_is_detected(self):
        domain = settings.EMAIL_TOKEN_DOMAIN_WHITELIST[0][0]

        form = EmailForm({
            'username': 'invalid@username.com',
            'domain': domain
        })

        assert not form.is_valid()


class TestEmailAuthView:
    def test_invalid_token(self, client):

        token = 'aninvalidtoken'

        url = reverse('email-auth-signin', kwargs=dict(token=token))

        response = client.get(url)

        assert response.status_code == 302
        assert response.url == '/email/invalid-token/'

    def test_expired_token(self, client):

        initial_datetime = dt.datetime.now()
        expired_datetime = initial_datetime + dt.timedelta(settings.EMAIL_TOKEN_TTL + 1)

        with freeze_time(initial_datetime) as frozen_time:

            token = EmailToken.objects.create_token('test@test.com')

            url = reverse('email-auth-signin', kwargs=dict(token=token))

            frozen_time.move_to(expired_datetime)

            response = client.get(url)

            assert response.status_code == 302
            assert response.url == '/email/invalid-token/'

    def test_next_url(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        response = client.get(url)

        assert response.status_code == 302
        assert response.url == 'https://myapp.com'

    def test_user_is_authenticated(self, client):

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.get(url)

        assert '_auth_user_id' in client.session

    def test_authentication_with_alternative_email(self, client):
        """Test user can authenticate with an alternative email"""

        user = UserFactory(email='test@test.com')
        user.emails.create(email='test@alternative.com')

        token = EmailToken.objects.create_token('test@test.com')

        url = '{}?next={}'.format(
            reverse('email-auth-signin', kwargs=dict(token=token)),
            'https://myapp.com'
        )

        client.get(url)

        assert '_auth_user_id' in client.session
