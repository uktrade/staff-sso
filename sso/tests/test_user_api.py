from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone

from .factories.oauth import AccessTokenFactory
from .factories.user import GroupFactory, UserFactory
from sso.oauth2.models import Application

pytestmark = [
    pytest.mark.django_db
]


def get_oauth_token(expires=None, user=None):

    if not user:
        user = UserFactory(
            email='user1@example.com',
            first_name='John',
            last_name='Doe'
        )

    user.groups.add(GroupFactory.create_batch(2)[1])  # create 2 groups but only assign the 2nd

    access_token = AccessTokenFactory(
        user=user,
        expires=expires or (timezone.now() + timedelta(days=1))
    )

    return access_token.token


class TestAPIGetUserMe:
    GET_USER_ME_URL = reverse_lazy('api-v1:user:me')

    def test_with_valid_token(self, api_client):
        """
        Test that with a valid token you can get the details of the logged in user.
        """
        token = get_oauth_token()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
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
        token = get_oauth_token(
            expires=timezone.now() - timedelta(minutes=1)
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 401
        assert response.json() == {
            'detail': 'Authentication credentials were not provided.'
        }

    def test_primary_and_related_emails(self, api_client):
        """Test email and related_emails keys are populated correctly given the app.email_ordering field"""
        emails = ['test@qqq.com', 'test@bbb.com', 'test@zzz.com', 'test@iii.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        token = get_oauth_token(user=user)

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