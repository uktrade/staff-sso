import pytest
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

    def test_introspect_view_with_email_priority_list(self, api_client):
        application = ApplicationFactory(email_ordering='vvv.com, ddd.com, ccc.com, bbb.com')

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com', email_list=['test@ccc.com', 'test@ddd.com', 'test@vvv.com'])

        intospect_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + intospect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 200
        assert response.json()['username'] == 'test@vvv.com'

    def test_introspect_view_with_immutable_email(self, api_client):
        application = ApplicationFactory(
            email_ordering='vvv.com, ddd.com, ccc.com, bbb.com',
            provide_immutable_email=True)

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com', email_list=['test@ccc.com', 'test@ddd.com', 'test@vvv.com'])

        intospect_token = AccessTokenFactory(
            application=application,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + intospect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 200
        assert response.json()['username'] == 'test@bbb.com'

    def test_can_only_introspect_tokens_belonging_to_same_application(self, api_client):
        """
        An introspect token for app1 should not be able to introspect tokens issued to app2.
        """

        application1 = ApplicationFactory()
        application2 = ApplicationFactory()

        introspect_user = UserFactory()
        user = UserFactory(email='test@bbb.com')

        intospect_token = AccessTokenFactory(
            application=application1,
            user=introspect_user,
            scope='introspection read'
        )

        token = AccessTokenFactory(
            application=application2,
            user=user
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + intospect_token.token)
        response = api_client.get(self.OAUTH2_INTROSPECTION_URL + f'?token={token.token}')

        assert response.status_code == 401
