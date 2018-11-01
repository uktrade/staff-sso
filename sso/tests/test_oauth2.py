import pytest

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from .factories.oauth import AccessTokenFactory, ApplicationFactory, UserFactory

pytestmark = [
    pytest.mark.django_db
]


class TestApplication:
    def test_get_email_order(self):
        """Test `get_email_order()` returns application order as a list"""
        order = ['aaa.com', 'bbb.com', 'ccc.com']

        app = ApplicationFactory(email_ordering=', '.join(order))

        assert app.get_email_order() == order

    def test_get_email_order_from_settings(self, settings):
        """Test `get_email_order()` returns order from settings when not specified on application"""
        order = ['aaa.com', 'bbb.com', 'ccc.com']

        settings.DEFAULT_EMAIL_ORDER = ', '.join(order)

        app = ApplicationFactory()

        assert app.get_email_order() == order

    def test_get_email_order_prefers_application_order(self, settings):
        """Test `get_email_order()` returns app order over settings"""

        order = ['aaa.com', 'bbb.com', 'ccc.com']

        settings_order = list(order)
        settings_order.reverse()

        settings.DEFAULT_EMAIL_ORDER = ', '.join(settings_order)

        app = ApplicationFactory(email_ordering=', '.join(order))

        assert app.get_email_order() == order

    def test_get_email_order_no_list_available(self, settings):
        """Test `get_email_order()` returns empty list when not defined on app or settings"""

        settings.DEFAULT_EMAIL_ORDER = ''

        app = ApplicationFactory()

        assert app.get_email_order() == []


class TestIntrospectView:
    OAUTH2_INTROSPECTION_URL = reverse('oauth2:introspect')

    def test_with_email_priority_list(self, api_client):
        application = ApplicationFactory(email_ordering='vvv.com, ddd.com, ccc.com, bbb.com')
        username = 'test@vvv.com'

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com', email_list=['test@ccc.com', 'test@ddd.com', 'test@vvv.com'])

        introspect_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + introspect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 200
        assert response.json()['username'] == username

        response_json = response.json()
        del response_json['exp']  # don't test expire time here

        assert response_json == {
            'access_type': 'client',
            'client_id': application.client_id,
            'username': username,
            'active': True,
            'scope': 'read',
            'unique_id': str(user.unique_id)
        }

    def test_with_immutable_email(self, api_client):
        application = ApplicationFactory(
            email_ordering='vvv.com, ddd.com, ccc.com, bbb.com',
            provide_immutable_email=True)

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com', email_list=['test@ccc.com', 'test@ddd.com', 'test@vvv.com'])

        introspect_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + introspect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 200
        assert response.json()['username'] == 'test@bbb.com'

    def test_fail_with_other_application_token(self, api_client):
        application1 = ApplicationFactory()
        application2 = ApplicationFactory()

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com')

        introspect_token = AccessTokenFactory(
            application=application1,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application2,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + introspect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 401

    def test_fail_with_invalid_token(self, api_client):
        """
        An introspect view should return {active: False} for invalid tokens
        """

        application = ApplicationFactory()

        introspect_user = UserFactory()
        UserFactory(email='test@bbb.com')

        introspect_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + introspect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token=invalid-token')

        assert response.status_code == 401

    def test_from_allowed_application(self, api_client):
        application = ApplicationFactory()
        other_application = ApplicationFactory()

        application.allow_tokens_from.add(other_application)

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com')

        application_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        other_application_token = AccessTokenFactory(
            application=other_application,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + application_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={other_application_token.token}')

        assert response.status_code == 200

        response_json = response.json()
        assert response_json['access_type'] == 'cross_client'
        assert response_json['source_name'] == application.name
        assert response_json['source_client_id'] == application.client_id
