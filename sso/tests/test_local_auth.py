import pytest
from django.conf import settings
from django.urls import reverse

from .factories.user import UserFactory

from sso.localauth.models import DomainWhitelist

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    user = UserFactory(email="user1@example.com")

    user.set_password("letmein2017")
    user.save()

    return user


class TestLogin:
    def test_user_can_authenticate(self, client, user):

        response = client.post(
            reverse("localauth:login"), {"username": user.email, "password": "letmein2017"}
        )

        assert response.status_code == 302
        assert response.url == reverse("saml2_logged_in")


class TestLogout:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("/local-url/", "/local-url/"),
            ("http://whitelisted.com/some/path/", "http://whitelisted.com/some/path/"),
            ("http://whitelisted.com", "http://whitelisted.com"),
            ("http://subdomain.whitelisted.com", settings.LOGOUT_REDIRECT_URL),
            ("https://danger.com", settings.LOGOUT_REDIRECT_URL),
        ],
    )
    def test_invalid_next_url(self, url, expected, client):
        user = UserFactory()

        client.force_login(user)

        DomainWhitelist.objects.create(domain="whitelisted.com")

        response = client.get(reverse("localauth:session-logout") + "?next=" + url)

        assert response.status_code == 302
        assert response.url == expected
