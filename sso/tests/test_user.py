from unittest import mock

import pytest

from sso.user.models import User
from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory

EMAIL = 'test@example.com'


class TestUserManager:
    @pytest.mark.django_db
    def test_create_superuser_basic(self):
        """
        Test that the `create_superuser` class method creates a superuser
        with the correct basic set of data.
        """
        assert User.objects.count() == 0

        user = User.objects.create_superuser(EMAIL, 'password')

        assert User.objects.count() == 1
        assert user.email == EMAIL
        assert user.password != 'password'
        assert user.is_superuser
        assert user.first_name == ''
        assert user.last_name == ''

    @pytest.mark.django_db
    def test_create_superuser_complete(self):
        """
        Test that the `create_superuser` class method creates a superuser
        with the correct full set of data.
        """
        assert User.objects.count() == 0

        user = User.objects.create_superuser(
            EMAIL,
            'password',
            first_name='John',
            last_name='Doe'
        )

        assert User.objects.count() == 1
        assert user.email == EMAIL
        assert user.password != 'password'
        assert user.is_superuser
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'

    @pytest.mark.django_db
    def test_create_superuser_without_email(self):
        """
        Test that the `create_superuser` class method raises `ValueError`
        if email is empty.
        """
        assert User.objects.count() == 0

        with pytest.raises(ValueError):
            User.objects.create_superuser(email='', password='password')


class TestUser:
    def test_is_staff_as_is_superuser(self):
        """
        Test that `is_staff` follows `is_superuser`.
        """
        user = User(email=EMAIL)

        user.is_superuser = True
        assert user.is_staff

        user.is_superuser = False
        assert not user.is_staff

    def test_get_full_name_with_first_last_name(self):
        """
        Test that `get_full_name()` == `first_name last_name`.
        """
        user = User(email=EMAIL, first_name='John', last_name='Doe')

        assert user.get_full_name() == 'John Doe'

    def test_get_full_name_with_first_name_only(self):
        """
        Test that `get_full_name()` == `first_name` if last_name is empty.
        """
        user = User(email=EMAIL, first_name='John')

        assert user.get_full_name() == 'John'

    def test_get_full_name_with_last_name_only(self):
        """
        Test that `get_full_name()` == `last_name` if first_name is empty.
        """
        user = User(email=EMAIL, last_name='Doe')

        assert user.get_full_name() == 'Doe'

    def test_get_full_name_with_email_only(self):
        """
        Test that `get_full_name()` == EMAIL if first/last name are empty.
        """
        user = User(email=EMAIL)

        assert user.get_full_name() == EMAIL

    def test_get_short_name(self):
        """
        Test that `get_short_name()` follows `get_full_name()`.
        """
        user = User()
        with mock.patch.object(user, 'get_full_name') as mock_get_full_name:
            mock_get_full_name.return_value = 'John Doe'
            assert user.get_short_name() == 'John Doe'

            mock_get_full_name.return_value = EMAIL
            assert user.get_short_name() == EMAIL

    @pytest.mark.django_db
    def test_can_access_with_perms(self):
        """
        Test that `can_access()` returns True when user assigned to app
        """

        user = UserFactory()
        app = ApplicationFactory(users=[user])

        assert user.can_access(app)

    @pytest.mark.django_db
    def test_can_access_without_perms(self):
        """
        Test that `can_access()` returns False when user is not assigned to app
        """

        app = ApplicationFactory()
        user = UserFactory()

        assert not user.can_access(app)

    @pytest.mark.django_db
    def test_can_access_with_app_default_access(self):
        """
        Test that `can_access()` returns True when user is not assigned to an app but the app allows default access
        """

        app = ApplicationFactory(default_access=True)
        user = UserFactory()

        assert user.can_access(app)

    @pytest.mark.django_db
    def test_can_access_without_app_default_access(self):
        """
        Test that `can_access()` returns False when user is not assigned to app and the app does not allow default
        access
        """

        app = ApplicationFactory(default_access=False)
        user = UserFactory()

        assert not user.can_access(app)
