import pytest

from .factories.oauth import ApplicationFactory


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

