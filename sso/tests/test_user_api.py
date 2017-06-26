from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone

from .factories.oauth import AccessTokenFactory
from .factories.user import GroupFactory, UserFactory

pytestmark = [
    pytest.mark.django_db
]


def get_oauth_token(expires=None):
    user = UserFactory(email='user1@example.com')
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
            'groups': [{
                'name': 'Group 2'
            }]
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
