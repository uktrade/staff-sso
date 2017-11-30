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

    @pytest.mark.django_db
    def test_user_emails_are_lower_cased(self):
        """
        Test that `save()` lower cases emails
        """
        assert User.objects.count() == 0

        email = 'ITATest1@example.com'

        user = User.objects.create(
            email=email,
            first_name='',
            last_name=''
        )

        assert user.email == email.lower()

    @pytest.mark.django_db
    def test_get_or_create_user_emails_are_lower_cased(self):
        """
        Test that `get_or_create()` lower cases emails
        """
        assert User.objects.count() == 0

        email = 'ITATest1@example.com'

        user, created = User.objects.get_or_create(
            email=email,
            first_name='',
            last_name=''
        )

        assert created

        assert user.email == email.lower()

    @pytest.mark.django_db
    def test_get_or_create_user_email_no_duplicates(self):
        """
        Test that `get_or_create()` lower cases emails
        """
        assert User.objects.count() == 0

        email = 'ITATest1@example.com'

        user, created = User.objects.get_or_create(
            email=email,
            first_name='',
            last_name=''
        )

        assert created

        user, created = User.objects.get_or_create(
            email=email,
            first_name='',
            last_name=''
        )

        assert not created

        assert user.email == email.lower()

    @pytest.mark.django_db
    def test_get_or_create_existing_user_queries_email_list(self):
        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

        user, created = User.objects.get_or_create(email='test@test.com')

        assert not created
        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

    @pytest.mark.django_db
    def test_get_or_create_new_user_adds_to_email_list(self):

        user, created = User.objects.get_or_create(email='test@test.com')

        assert created
        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'


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

        app = ApplicationFactory(default_access_allowed=True)
        user = UserFactory()

        assert user.can_access(app)

    @pytest.mark.django_db
    def test_can_access_without_app_default_access(self):
        """
        Test that `can_access()` returns False when user is not assigned to app and the app does not allow default
        access
        """

        app = ApplicationFactory(default_access_allowed=False)
        user = UserFactory()

        assert not user.can_access(app)

    @pytest.mark.django_db
    def test_get_emails_for_application_app_email_ordering(self):
        app = ApplicationFactory(email_ordering='aaa.com, bbb.com, ccc.com, ddd.com, eee.com')

        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@aaa.com'
        emails.pop(emails.index(primary_email))
        assert set(related_emails) == set(emails)

    @pytest.mark.django_db
    def test_get_emails_for_application_settings_email_ordering(self, settings):
        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        app = ApplicationFactory()

        settings.DEFAULT_EMAIL_ORDER = 'bbb.com, zzz.com'

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@bbb.com'
        emails.pop(emails.index('test@bbb.com'))
        assert set(related_emails) == set(emails)

    @pytest.mark.django_db
    def test_get_emails_for_application_settings_no_ordering(self):
        """Sanity check to confirm that something is returned with no specific ordering applied"""
        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        app = ApplicationFactory()

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email in emails
        emails.pop(emails.index(primary_email))
        assert set(emails) == set(related_emails)

    @pytest.mark.django_db
    def test_get_emails_for_application_emails_not_in_priority_list(self):
        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        app = ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com')

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email in emails
        emails.pop(emails.index(primary_email))
        assert set(emails) == set(related_emails)

    @pytest.mark.django_db
    def test_get_emails_for_application_emails_no_application(self):
        ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com', provide_immutable_email=False)

        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(None)

        assert primary_email == 'test@google.com'
        assert set(related_emails) == set(emails[1:])

    @pytest.mark.django_db
    def test_get_emails_for_application_emails_immutable_email(self):
        app = ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com', provide_immutable_email=True)

        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@google.com'
        assert set(related_emails) == set(emails[1:])

    @pytest.mark.django_db
    def test_save_adds_to_email_list(self):
        user = User()

        user.email = 'test@test.com'

        user.save()

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

    @pytest.mark.django_db
    def test_save_email_already_in_email_list(self):
        """Sanity check to confirm `save()` won't try add additional user.emails related objects"""
        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1

        user.save()

        assert user.emails.count() == 1

    @pytest.mark.django_db
    def test_emails_create(self):

        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

        user.emails.create(email='test222@test.com')

        assert user.emails.count() == 2
        assert user.emails.last().email == 'test222@test.com'
