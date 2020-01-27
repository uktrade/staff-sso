import datetime
from unittest import mock

import pytest
from freezegun import freeze_time
from django.utils import timezone

from sso.user.middleware import UpdatedLastAccessedMiddleware
from sso.user.models import AccessProfile, User

from .factories.oauth import ApplicationFactory
from .factories.saml import SamlApplicationFactory
from .factories.user import UserFactory


pytestmark = [
    pytest.mark.django_db
]

EMAIL = 'test@example.com'


class TestUserManager:
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

    def test_create_superuser_without_email(self):
        """
        Test that the `create_superuser` class method raises `ValueError`
        if email is empty.
        """
        assert User.objects.count() == 0

        with pytest.raises(ValueError):
            User.objects.create_superuser(email='', password='password')

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

    def test_get_or_create_existing_user_queries_email_list(self):
        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

        user, created = User.objects.get_or_create(email='test@test.com')

        assert not created
        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

    def test_get_or_create_new_user_adds_to_email_list(self):

        user, created = User.objects.get_or_create(email='test@test.com')

        assert created
        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

    @pytest.mark.parametrize(
        'email',
        (
            'user@example.com',
            'USER@EXAMPLE.COM',
        ),
    )
    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_set_email_last_login_time(self, email):
        user = UserFactory(email='user@example.com')
        assert user.emails.count() == 1
        email_obj = user.emails.first()
        assert email_obj.last_login is None
        assert email_obj.email == 'user@example.com'

        User.objects.set_email_last_login_time(email)

        assert user.emails.count() == 1
        email_obj = user.emails.first()
        assert user.emails.first().last_login == timezone.now()
        assert email_obj.email == 'user@example.com'


class TestUser:

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

    def test_can_access_with_perms(self):
        """
        Test that `can_access()` returns True when user assigned to app
        """

        user = UserFactory()
        app = ApplicationFactory(users=[user])

        assert user.can_access(app)

    def test_cannot_access_without_perms(self):
        """
        Test that `can_access()` returns False when user is not assigned to app
        """

        app = ApplicationFactory()
        user = UserFactory()

        assert not user.can_access(app)

    def test_can_access_saml2_with_access_profile(self):
        app = SamlApplicationFactory()
        user = UserFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.saml2_applications.add(app)
        user.access_profiles.add(ap)

        assert user.can_access(app)

    def test_can_access_saml2_without_access_profile_false(self):
        app = SamlApplicationFactory()
        user = UserFactory()
        assert not user.can_access(app)

    def test_can_access_saml2_if_app_disabled(self):
        app = SamlApplicationFactory(enabled=False)
        user = UserFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.saml2_applications.add(app)
        user.access_profiles.add(ap)

        assert not user.can_access(app)

    def test_can_access_with_access_profile(self):

        app = ApplicationFactory()
        user = UserFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.oauth2_applications.add(app)
        user.access_profiles.add(ap)

        assert user.can_access(app)

    def test_can_access_with_access_profile_that_does_not_include_application(self):
        """The user has an access profile but it doesn't provide access to the app"""

        app = ApplicationFactory()
        user = UserFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.oauth2_applications.add(app)
        ap2 = AccessProfile.objects.create(name='test profile 2')
        user.access_profiles.add(ap2)

        assert not user.can_access(app)

    def test_user_has_multiple_profiles_can_access_application(self):
        """The user has multiple profiles, only one grants them access to the application"""

        app = ApplicationFactory()
        user = UserFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.oauth2_applications.add(app)
        ap2 = AccessProfile.objects.create(name='test profile 2')
        user.access_profiles.add(ap)
        user.access_profiles.add(ap2)

        assert user.can_access(app)

    def test_user_permitted_application_but_not_profile(self):
        """User is permitted to access an application directly but does not have profile based access"""

        user = UserFactory()
        app = ApplicationFactory(users=[user])
        ap = AccessProfile.objects.create(name='test profile')
        user.access_profiles.add(ap)
        assert user.can_access(app)

    def test_user_permitted_application_but_permitted_via_profile(self):
        """User is not granted direct access (permitted_applications) but has profile based access"""

        user = UserFactory()
        app = ApplicationFactory()
        ap = AccessProfile.objects.create(name='test profile')
        ap.oauth2_applications.add(app)
        user.access_profiles.add(ap)
        assert user.can_access(app)

    def test_can_access_with_app_default_access(self):
        """
        Test that `can_access()` returns True when user is not assigned to an app but the app allows default access
        """

        app = ApplicationFactory(default_access_allowed=True)
        user = UserFactory()

        assert user.can_access(app)

    def test_can_access_without_app_default_access(self):
        """
        Test that `can_access()` returns False when user is not assigned to app and the app does not allow default
        access
        """

        app = ApplicationFactory(default_access_allowed=False)
        user = UserFactory()

        assert not user.can_access(app)

    def test_can_access_with_email(self):
        """
        Test that `can_access()` returns True when the user's email is in the
        `Application.allow_access_by_email_suffix` list
        """
        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )

        user = UserFactory(email='hello@notinlist.com')

        assert not user.can_access(app)

        user = UserFactory(email='joe.blogs@testing.com')
        assert user.can_access(app)

    def test_get_emails_for_application_app_email_ordering(self):
        app = ApplicationFactory(email_ordering='aaa.com, bbb.com, ccc.com, ddd.com, eee.com')

        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@aaa.com'
        emails.pop(emails.index(primary_email))
        assert set(related_emails) == set(emails)

    def test_get_emails_for_application_settings_email_ordering(self, settings):
        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        app = ApplicationFactory()

        settings.DEFAULT_EMAIL_ORDER = 'bbb.com, zzz.com'

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@bbb.com'
        emails.pop(emails.index('test@bbb.com'))
        assert set(related_emails) == set(emails)

    def test_get_emails_for_application_settings_no_ordering(self):
        """Sanity check to confirm that something is returned with no specific ordering applied"""
        emails = ['test@zzz.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        app = ApplicationFactory()

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email in emails
        emails.pop(emails.index(primary_email))
        assert set(emails) == set(related_emails)

    def test_get_emails_for_application_emails_not_in_priority_list(self):
        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        app = ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com')

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email in emails
        emails.pop(emails.index(primary_email))
        assert set(emails) == set(related_emails)

    def test_get_emails_for_application_emails_no_application(self):
        ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com', provide_immutable_email=False)

        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(None)

        assert primary_email == 'test@google.com'
        assert set(related_emails) == set(emails[1:])

    def test_get_emails_for_application_emails_immutable_email(self):
        app = ApplicationFactory(email_ordering='bbb.com, ccc.com, ddd.com', provide_immutable_email=True)

        emails = ['test@google.com', 'test@microsoft.com', 'test@yahoo.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        primary_email, related_emails = user.get_emails_for_application(app)

        assert primary_email == 'test@google.com'
        assert set(related_emails) == set(emails[1:])

    def test_save_adds_to_email_list(self):
        user = User()

        user.email = 'test@test.com'

        user.save()

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

    def test_save_email_already_in_email_list(self):
        """Sanity check to confirm `save()` won't try add additional user.emails related objects"""
        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1

        user.save()

        assert user.emails.count() == 1

    def test_emails_create(self):

        user = UserFactory(email='test@test.com')

        assert user.emails.count() == 1
        assert user.emails.first().email == 'test@test.com'

        user.emails.create(email='test222@test.com')

        assert user.emails.count() == 2
        assert user.emails.last().email == 'test222@test.com'

    def test_emails_added_on_save_are_lowercase(self):

        user = User.objects.create(email='TEST@TEST.COM')

        assert user.emails.count() == 1
        assert user.emails.last().email == 'test@test.com'

    def test_emails_added_directly_to_list_are_lower_cased(self):
        user = UserFactory(email='test@test.com')

        user.emails.create(email='UPPER@CASE.COM')

        assert user.emails.count() == 2
        assert user.emails.last().email == 'upper@case.com'

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_user_last_accessed_field_updates(self, rf, mocker):

        user = UserFactory(email='goblin@example.com')
        middleware = UpdatedLastAccessedMiddleware(get_response=mocker.MagicMock())

        request = rf.get('/')
        request.user = user

        assert user.last_accessed is None
        middleware(request)

        assert request.user.last_accessed == datetime.datetime.now(tz=datetime.timezone.utc)
        assert User.objects.get(pk=user.pk).last_accessed == datetime.datetime.now(tz=datetime.timezone.utc)

    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_user_last_accessed_field_updates_integration_test(self, client):
        user = UserFactory(email='goblin@example.com')
        user.set_password('12345')
        user.save()

        client.login(email='goblin@example.com', password='12345')
        response = client.get('/')

        assert User.objects.get(pk=user.pk).last_accessed == datetime.datetime.now(tz=datetime.timezone.utc)

    def test_email_user_id_is_created_on_save(self, settings):
        user = User()
        user.email = 'test@test.com'

        assert not user.email_user_id

        user.save()

        user.refresh_from_db()

        hash = str(user.user_id)[:8]

        assert user.email_user_id == f'test-{hash}{settings.EMAIL_ID_DOMAIN}'

    def test_email_user_id_is_not_overwritten(self):
        user = UserFactory(email='goblin@example.com')

        current_id = user.email_user_id

        assert current_id is not None

        user.save()

        user.refresh_from_db()

        assert current_id == user.email_user_id


class TestAccessProfile:
    def test_is_allowed_true(self):
        app = ApplicationFactory()

        ap = AccessProfile.objects.create()
        ap.oauth2_applications.add(app)

        assert ap.is_allowed(app)

    def test_is_access_allowed_false(self):
        app = ApplicationFactory()

        ap = AccessProfile.objects.create()

        assert not ap.is_allowed(app)

    def test_saml2_is_access_alowed_true(self):
        app = SamlApplicationFactory()

        ap = AccessProfile.objects.create()
        ap.saml2_applications.add(app)

        assert ap.is_allowed(app)

    def test_saml2_is_access_allowed_false(self):
        app = SamlApplicationFactory()

        ap = AccessProfile.objects.create()
        ap.saml2_applications.add(app)

        assert ap.is_allowed(app)

    def test_saml2_is_access_allowed_if_app_is_disabled(self):

        app = SamlApplicationFactory(enabled=False)

        ap = AccessProfile.objects.create()
        ap.saml2_applications.add(app)

        assert not ap.is_allowed(app)

    def test_user_get_permitted_applications(self):
        ap = AccessProfile.objects.create()
        user = UserFactory(email='goblin@example.com', add_access_profiles=[ap])

        app1 = ApplicationFactory(
            application_key='app-1',
            display_name='Appplication 1',
            start_url='https://application1.com',
            users=[user])
        app2 = ApplicationFactory(
            application_key='app-2',
            display_name='Appplication 2',
            start_url='https://application2.com',
            users=[user])
        app3 = ApplicationFactory(
            application_key='app-3',
            display_name='Appplication 3',
            start_url='https://application3.com',
            users=[user])

        ap.oauth2_applications.add(app1)
        ap.oauth2_applications.add(app3)

        permitted_applications = user.get_permitted_applications()

        assert len(permitted_applications) == 3
        assert sorted(permitted_applications, key=lambda x: x['key']) == [
            {
                'key': app1.application_key,
                'url': app1.start_url,
                'name': app1.display_name
            },
            {
                'key': app2.application_key,
                'url': app2.start_url,
                'name': app2.display_name
            },
            {
                'key': app3.application_key,
                'url': app3.start_url,
                'name': app3.display_name
            }
        ]

    def test_user_get_permitted_applications_public_only(self):
        ap = AccessProfile.objects.create()
        user = UserFactory(email='goblin@example.com', add_access_profiles=[ap])

        app1 = ApplicationFactory(
            application_key='app-1',
            display_name='Appplication 1',
            start_url='https://application1.com',
            public=True,
            users=[user])
        ApplicationFactory(
            application_key='app-2',
            display_name='Appplication 2',
            start_url='https://application2.com',
            public=False,
            users=[user])

        permitted_applications = user.get_permitted_applications(public_only=True)

        assert len(permitted_applications) == 1
        assert permitted_applications == [
            {
                'key': app1.application_key,
                'url': app1.start_url,
                'name': app1.display_name
            }
        ]

