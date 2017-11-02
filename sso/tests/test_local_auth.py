import pytest
from django.urls import reverse

from .factories.user import UserFactory

pytestmark = [
    pytest.mark.django_db
]


@pytest.fixture
def user():
    user = UserFactory(email='user1@example.com')

    user.set_password('letmein2017')
    user.save()

    return user


class TestLogin:
    def test_user_can_authenticate(self, client, user):

        response = client.post(
            reverse('localauth:login'),
            {'username': user.email, 'password': 'letmein2017'})

        assert response.status_code == 302
        assert response.url == reverse('saml2_logged_in')

