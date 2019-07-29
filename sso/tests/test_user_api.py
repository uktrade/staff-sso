from datetime import timedelta

import pytest
from django.urls import reverse_lazy
from django.utils import timezone

from sso.oauth2.models import Application

from .factories.oauth import AccessTokenFactory, ApplicationFactory
from .factories.saml import SamlApplicationFactory
from .factories.user import GroupFactory, UserFactory, AccessProfileFactory

pytestmark = [
    pytest.mark.django_db
]


def get_oauth_token(expires=None, user=None, scope='read'):

    if not user:
        user = UserFactory(
            email='user1@example.com',
            first_name='John',
            last_name='Doe'
        )

    user.groups.add(GroupFactory.create_batch(2)[1])  # create 2 groups but only assign the 2nd

    application = ApplicationFactory(default_access_allowed=True)

    access_token = AccessTokenFactory(
        application=application,
        user=user,
        expires=expires or (timezone.now() + timedelta(days=1)),
        scope=scope
    )

    return user, access_token.token


class TestAPIGetUserMe:
    GET_USER_ME_URL = reverse_lazy('api-v1:user:me')

    def test_with_valid_token(self, api_client):
        """
        Test that with a valid token you can get the details of the logged in user.
        """
        user, token = get_oauth_token()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': [],
            'groups': [],
            'permitted_applications': [],
            'access_profiles': []
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
        _, token = get_oauth_token(
            expires=timezone.now() - timedelta(minutes=1)
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 401
        assert response.json() == {
            'detail': 'Authentication credentials were not provided.'
        }

    def test_primary_and_related_emails_using_priority_list(self, api_client):
        """Test email and related_emails keys are populated correctly given the app.email_ordering field"""
        emails = ['test@qqq.com', 'test@bbb.com', 'test@zzz.com', 'test@iii.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.email_ordering = 'zzz.com, aaa.com, bbb.com'
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        data = response.json()

        assert data['email'] == 'test@zzz.com'
        emails.pop(emails.index('test@zzz.com'))

        assert set(data['related_emails']) == set(emails)

    def test_primary_and_related_emails_using_with_immutable_email(self, api_client):
        """Test email and related_emails keys are populated correctly given the app.email_ordering field"""
        emails = ['test@qqq.com', 'test@bbb.com', 'test@zzz.com', 'test@iii.com']

        user = UserFactory(email=emails[0], email_list=emails[1:])

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.email_ordering = 'zzz.com, aaa.com, bbb.com'
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_ME_URL)

        assert response.status_code == 200
        data = response.json()

        assert data['email'] == 'test@qqq.com'
        emails.pop(emails.index('test@qqq.com'))

        assert set(data['related_emails']) == set(emails)

    def test_patch_user_details(self, api_client):
        """Test contact_email first_name and last_name keys are updated correctly on a patch request"""
        email = 'test@qqq.com'

        user = UserFactory(email=email)

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.patch(self.GET_USER_ME_URL, {
            'first_name': 'Jane',
            'last_name': 'Dough',
            'contact_email': 'jd@test.qqq'
        }, format='json')

        assert response.status_code == 200

    def test_patch_user_first_name(self, api_client):
        """Test first_name is updated correctly on a patch request"""
        email = 'test@qqq.com'

        user = UserFactory(email=email)

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.patch(self.GET_USER_ME_URL, {
            'first_name': 'Jane',
        }, format='json')

        assert response.status_code == 200

    def test_patch_user_with_valid_contact_email(self, api_client):
        """Test contact_email is updated correctly on a patch request"""
        email = 'test@qqq.com'

        user = UserFactory(email=email)

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.patch(self.GET_USER_ME_URL, {
            'contact_email': 'jd@test.qqq',
        }, format='json')

        assert response.status_code == 200

    def test_patch_user_with_invalid_contact_email(self, api_client):
        """Test invalid contact_email is handled correctly on a patch request"""
        email = 'test@qqq.com'

        user = UserFactory(email=email)

        _, token = get_oauth_token(user=user)

        assert Application.objects.count() == 1

        app = Application.objects.first()
        app.provide_immutable_email = True
        app.save()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.patch(self.GET_USER_ME_URL, {
            'contact_email': 'not_an_email',
        }, format='json')

        assert response.status_code == 400

        data = response.json()
        assert data['contact_email'] == ['Enter a valid email address.']


class TestApiUserIntrospect:
    GET_USER_INTROSPECT_URL = reverse_lazy('api-v1:user:user-introspect')

    def test_with_valid_token_and_email(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=user1@example.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': [],
            'groups': [],
            'permitted_applications': [],
            'access_profiles': []
        }

    def test_with_valid_token_and_email_alias(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        user.emails.create(email='test@aaa.com')
        user.emails.create(email='test@bbb.com')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': ['test@bbb.com', 'test@aaa.com'],
            'groups': [],
            'permitted_applications': [],
            'access_profiles': []
        }

    def test_with_valid_token_and_access_profile(self, api_client):
        ap = AccessProfileFactory()
        user, token = get_oauth_token(scope='introspection')
        user.access_profiles.add(ap)

        user.emails.create(email='test@aaa.com')
        user.emails.create(email='test@bbb.com')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': ['test@bbb.com', 'test@aaa.com'],
            'groups': [],
            'permitted_applications': [],
            'access_profiles': [ap.slug]
        }

    def test_with_valid_token_and_permitted_applications(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        app = ApplicationFactory(users=[user])

        user.emails.create(email='test@aaa.com')
        user.emails.create(email='test@bbb.com')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': ['test@bbb.com', 'test@aaa.com'],
            'groups': [],
            'permitted_applications': [{'key': app.application_key, 'name': app.display_name, 'url': app.start_url}],
            'access_profiles': []
        }

    def test_with_user_id(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        app = ApplicationFactory(users=[user])
        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?user_id={}'.format(str(user.user_id)))

        assert response.status_code == 200
        assert response.json() == {
            'email': 'user1@example.com',
            'user_id': str(user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'related_emails': [],
            'groups': [],
            'permitted_applications': [{'key': app.application_key, 'name': app.display_name, 'url': app.start_url}],
            'access_profiles': []
        }

    def test_requires_email_or_user_id(self, api_client):
        user, token = get_oauth_token(scope='introspection')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL)

        assert response.status_code == 400

    def test_without_introspect_scope(self, api_client):
        user, token = get_oauth_token(scope='read')

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email=test@aaa.com')

        assert response.status_code == 403

    def test_honours_user_permissioms(self, api_client):
        """
        If an Oauth2 app attempts to introspect a user who does not have permissions to accesss
        that application then it should not return user info
        """
        user, token = get_oauth_token(scope='introspection')

        assert Application.objects.count() == 1
        app = Application.objects.first()
        app.default_access_allowed = False
        app.save()

        introspected_user = UserFactory(email='test@aaa.com')  # noqa: F841

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_INTROSPECT_URL + '?email={introspected_user.email}')

        assert response.status_code == 400


class TestAPISearchUsers:
    GET_USER_SEARCH_URL = reverse_lazy('api-v1:user:user-search')

    def setup_seach_user(self):
        search_user = UserFactory(
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe'
        )
        search_user.groups.add(GroupFactory())

        def_oauth_app = ApplicationFactory(default_access_allowed=True)
        access_token = AccessTokenFactory(
            application=def_oauth_app,
            user=search_user,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )
        return search_user, def_oauth_app, access_token.token

    def test_all_users_with_only_search_user(self, api_client):
        #   default access
        search_user, oauth_app, token = self.setup_seach_user()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json() == [
            {
                'user_id': str(search_user.user_id),
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com',
            }
        ]

    @pytest.mark.django_db
    def test_autocomplete_filter_only_search_user_first_name(self, api_client):
        search_user, oauth_app, token = self.setup_seach_user()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.get(self.GET_USER_SEARCH_URL + '?autocomplete=john')

        assert response.status_code == 200
        assert response.json() == [{
            'user_id': str(search_user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
        }]

    @pytest.mark.django_db
    def test_autocomplete_filter_only_search_user_first_name_part(self, api_client):
        search_user, oauth_app, token = self.setup_seach_user()

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        response = api_client.get(self.GET_USER_SEARCH_URL + '?autocomplete=jo')

        assert response.status_code == 200
        assert response.json() == [{
            'user_id': str(search_user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
        }]

    @pytest.mark.django_db
    def test_all_users_with_user_with_default_access_user(self, api_client):
        #   default access
        search_user, oauth_app, token = self.setup_seach_user()
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.groups.add(GroupFactory())
        oauth_app.users.add(user1)

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.django_db
    def test_all_users_scenario_1(self, api_client):
        """
        searching with an app that has default_access_allowed True
        so api lists all users, regardless of app access
        """
        search_user, def_oauth_app, token = self.setup_seach_user()
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.groups.add(GroupFactory())
        def_oauth_app.users.add(user1)

        # add a different user to different app
        oauth_app = ApplicationFactory()
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        oauth_app.users.add(user2)

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 3

        response = api_client.get(self.GET_USER_SEARCH_URL + '?autocomplete=john')

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json() == [{
            'user_id': str(search_user.user_id),
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
        }]

        response = api_client.get(self.GET_USER_SEARCH_URL + '?autocomplete=first')

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.django_db
    def test_all_users_scenario_2(self, api_client):
        """
        searching with an app that has default_access_allowed False
        so api lists only users with access to that app,
        none of the others should appear
        """
        search_user, def_oauth_app, token = self.setup_seach_user()
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.groups.add(GroupFactory())
        def_oauth_app.users.add(user1)

        # add a different user to different app
        oauth_app = ApplicationFactory(default_access_allowed=False)
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        oauth_app.users.add(user2)
        access_token = AccessTokenFactory(
            application=oauth_app,
            user=user2,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.django_db
    def test_all_users_scenario_3(self, api_client):
        """
        searching with an app that has default_access_allowed False
        so api lists only users with access to that app via direct app access
        none of the others should appear
        """
        oauth_app_1 = ApplicationFactory(default_access_allowed=False)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.groups.add(GroupFactory())
        oauth_app_1.users.add(user1)

        # add a different user to different app
        oauth_app_2 = ApplicationFactory(default_access_allowed=False)
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        oauth_app_2.users.add(user2)
        access_token = AccessTokenFactory(
            application=oauth_app_2,
            user=user2,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.django_db
    def test_list_all_users_access_profile(self, api_client):
        """
        searching with an app that has default_access_allowed False
        so api lists only users with access to that app via access profile
        none of the others should appear
        """
        ap = AccessProfileFactory()
        oauth_app_1 = ApplicationFactory(default_access_allowed=False)
        ap.oauth2_applications.add(oauth_app_1)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.access_profiles.add(ap)

        user1.emails.create(email='test@aaa.com')
        user1.emails.create(email='test@bbb.com')
        access_token = AccessTokenFactory(
            application=oauth_app_1,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.django_db
    def test_list_all_users_access_profile_and_permitted_app(self, api_client):
        """
        searching with an app that has default_access_allowed False
        so api lists only users with access to that app via
        access profile or direct app access
        none of the others should appear
        """
        # a user with access profile
        ap = AccessProfileFactory()
        oauth_app_1 = ApplicationFactory(default_access_allowed=False)
        ap.oauth2_applications.add(oauth_app_1)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.access_profiles.add(ap)

        user1.emails.create(email='test@aaa.com')
        user1.emails.create(email='test@bbb.com')

        # a user with permitted application
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        oauth_app_1.users.add(user2)

        access_token = AccessTokenFactory(
            application=oauth_app_1,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.django_db
    def test_all_users_saml_app_enabled(self, api_client):
        search_user, def_oauth_app, token = self.setup_seach_user()
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', enabled=True)
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1',
            add_access_profiles=[ap]
        )
        access_token = AccessTokenFactory(
            application=def_oauth_app,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.django_db
    def test_list_users_can_access_with_domain(self, api_client):
        """
        Test that `can_access()` returns True when the user's email is in the
        `Application.allow_access_by_email_suffix` list
        """
        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )

        user = UserFactory(email='hello@example.com')

        assert not user.can_access(app)

        user = UserFactory(email='joe.blogs@testing.com')
        assert user.can_access(app)

        access_token = AccessTokenFactory(
            application=app,
            user=user,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.django_db
    def test_list_users_with_access_by_domain_and_permitted_apps(self, api_client):
        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )

        user1 = UserFactory(email='hello@example.com')

        assert not user1.can_access(app)

        app.users.add(user1)
        assert user1.can_access(app)

        user2 = UserFactory(email='joe.blogs@testing.com')
        assert user2.can_access(app)

        access_token = AccessTokenFactory(
            application=app,
            user=user2,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.django_db
    def test_list_access_by_domain_and_permitted_app_and_access_profile(self, api_client):
        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )
        user = UserFactory(email='joe.blogs@testing.com')
        assert user.can_access(app)

        # a user with access profile
        ap = AccessProfileFactory()
        ap.oauth2_applications.add(app)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.access_profiles.add(ap)

        # a user with permitted application
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        app.users.add(user2)

        access_token = AccessTokenFactory(
            application=app,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        print(response.json())
        assert len(response.json()) == 3

    @pytest.mark.django_db
    def test_list_access_by_domain_and_permitted_app_and_access_profile_related_emails(self, api_client):
        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )
        user = UserFactory(email='joe.blogs@testing.com')
        assert user.can_access(app)

        # a user with access profile
        ap = AccessProfileFactory()
        ap.oauth2_applications.add(app)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.access_profiles.add(ap)

        # add few more emails, to check distinctness
        user1.emails.create(email='test@aaa.com')
        user1.emails.create(email='test@bbb.com')

        # a user with permitted application
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        app.users.add(user2)

        access_token = AccessTokenFactory(
            application=app,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.django_db
    def test_all_users_scenario_5(self, api_client):
        """
        checking all users scenario, when we have all kinds of users
        including saml
        a request with default_access_allowed, should get all
        users back, none filtered
        """
        search_user, def_oauth_app, token = self.setup_seach_user()
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', enabled=True)
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        saml_user = UserFactory(
            email='saml.user@example.com',
            first_name='Saml',
            last_name='User',
            add_access_profiles=[ap]
        )

        app = ApplicationFactory(
            default_access_allowed=False,
            allow_access_by_email_suffix='testing.com, testing123.com'
        )
        user = UserFactory(email='joe.blogs@testing.com')
        assert user.can_access(app)

        # a user with access profile
        ap1 = AccessProfileFactory()
        ap1.oauth2_applications.add(app)
        user1 = UserFactory(
            email='first1.last1@example.com',
            first_name='First1',
            last_name='Last1'
        )
        user1.access_profiles.add(ap)

        # add few more emails, to check distinctness
        user1.emails.create(email='test@aaa.com')
        user1.emails.create(email='test@bbb.com')

        # a user with permitted application
        user2 = UserFactory(
            email='first2.last2@example.com',
            first_name='First2',
            last_name='Last2'
        )
        user2.groups.add(GroupFactory())
        app.users.add(user2)

        access_token = AccessTokenFactory(
            application=def_oauth_app,
            user=user1,
            expires=(timezone.now() + timedelta(days=1)),
            scope='search'
        )

        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token.token)
        response = api_client.get(self.GET_USER_SEARCH_URL)

        assert response.status_code == 200
        assert len(response.json()) == 5
