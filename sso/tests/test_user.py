import pytest

from sso.user.models import User

EMAIL = 'test@example.com'


class TestUserManager:
    @pytest.mark.django_db
    def test_create_superuser(self):
        """
        Test that the `create_superuser` class method creates a superuser
        with the correct data.
        """
        assert User.objects.count() == 0

        user = User.objects.create_superuser(EMAIL, 'password')

        assert User.objects.count() == 1
        assert user.email == EMAIL
        assert user.password != 'password'
        assert user.is_superuser

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

    def test_get_full_name_as_email(self):
        """
        Test that `get_full_name()` follows `email`.
        """
        user = User(email=EMAIL)

        assert user.get_full_name() == EMAIL

    def test_get_short_name(self):
        """
        Test that `get_short_name()` follows `email`.
        """
        user = User(email=EMAIL)

        assert user.get_short_name() == EMAIL
