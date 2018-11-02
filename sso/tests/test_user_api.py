from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone

from sso.oauth2.models import Application

from .factories.oauth import AccessTokenFactory, ApplicationFactory
from .factories.user import GroupFactory, UserFactory

pytestmark = [
    pytest.mark.django_db
]


def get_oauth_token(expires=None, user=None, scope='read'):

    if not user:
        user = UserFactory(
            email='user1@example.com',
            first_name='John',
            last_name='Doe'
        )

    user.groups.add(GroupFactory.create_batch(2)[1])  # create 2 groups but only assign the 2nd

    application = ApplicationFactory(default_access_allowed=True)

    access_token = AccessTokenFactory(
        application=application,
        user=user,
        expires=expires or (timezone.now() + timedelta(days=1)),
        scope=scope
    )

    return user, access_token.token


class TestAPIGetUserMe:
    GET_USER_ME_URL = reverse_lazy('api-v1:user:me')

    def test_with_valid_token(self, api_client):
        """
        Test that with a valid token you can get the details of the logged in user.
        """
        user, token = get_oauth_token()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': [],
            'groups': []
        }

    def test_fails_with_invalid_token(self, api_client):
        """
        Test that with a invalid token you cannot get the details of the logged in user.
        """
        get_oauth_token()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 401
        assert response.json() == {
            'detail': 'Authentication credentials were not provided.'
        }

    def test_fails_with_expired_token(self, api_client):
        """
        Test that with an expired token you cannot get the details of the logged in user.
        """
        _, token = get_oauth_token(
            expires=timezone.now() - timedelta(minutes=1)
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 401
        assert response.json() == {
            'detail': 'Authentication credentials were not provided.'
        }

    def test_primary_and_related_emails_using_priority_list(self, api_client):
        """Test email and related_emails keys are populated correctly given the app.email_ordering field"""
        emails = ['test@qqq.com', 'test@bbb.com', 'test@zzz.com', 'test@iii.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.email_ordering = 'zzz.com, aaa.com, bbb.com'
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        data = response.json()

        assert data['email'] == 'test@zzz.com'
        emails.pop(emails.index('test@zzz.com'))

        assert set(data['related_emails']) == set(emails)

    def test_primary_and_related_emails_using_with_immutable_email(self, api_client):
        """Test email and related_emails keys are populated correctly given the app.email_ordering field"""
        emails = ['test@qqq.com', 'test@bbb.com', 'test@zzz.com', 'test@iii.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.email_ordering = 'zzz.com, aaa.com, bbb.com'
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        data = response.json()

        assert data['email'] == 'test@qqq.com'
        emails.pop(emails.index('test@qqq.com'))

        assert set(data['related_emails']) == set(emails)


class TestApiUserIntrospect:
    GET_USER_INTROSPECT_URL = reverse_lazy('api-v1:user:user-introspect')

    def test_with_valid_token_and_email(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=user1@example.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': [],
            'groups': []
        }

    def test_with_valid_token_and_email_alias(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        user.emails.create(email='test@aaa.com')
        user.emails.create(email='test@bbb.com')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': ['test@bbb.com', 'test@aaa.com'],
            'groups': []
        }

    def test_requires_email(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL)

        assert response.status_code == 400

    def test_without_introspect_scope(self, api_client):
        user, token = get_oauth_token(scope='read')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 403

    def test_honours_user_permissioms(self, api_client):
        """
        If an Oauth2 app attempts to introspect a user who does not have permissions to accesss
        that application then it should not return user info
        """
        user, token = get_oauth_token(scope='introspection')

        assert Application.objects.count() == 1
        app = Application.objects.first()
        app.default_access_allowed = False
        app.save()

        introspected_user = UserFactory(email='test@aaa.com')  # noqa: F841

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email={introspected_user.email}')

        assert response.status_code == 400
