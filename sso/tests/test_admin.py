import re

import pytest

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.shortcuts import reverse

from sso.user.admin import UserAdmin
from sso.user.admin_views import ShowUserPermissionsView

from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory


pytestmark = [
    pytest.mark.django_db
]

User = get_user_model()


class TestShowUserPermissionsView:
    def test_view_requires_authentication(self, rf):
        request = rf.get(reverse('show-permissions-view', kwargs={'user_id': 25}))
        request.user = AnonymousUser()

        response = ShowUserPermissionsView.as_view()(request)

        assert response.status_code == 302
        assert response.url.startswith('/admin/login/')

    def test_users_name_appears_on_page(self, rf):
        admin_user = UserFactory(is_superuser=True, is_staff=True)
        user = UserFactory(first_name='Bill', last_name='Smith')

        request = rf.get(reverse('show-permissions-view', kwargs={'user_id': user.id}))
        request.user = admin_user

        response = ShowUserPermissionsView.as_view()(request, user_id=user.id)

        content = response.content.decode('utf-8')

        assert response.status_code == 200
        assert 'User: {}'.format(user.get_full_name()) in content

    def test_application_permissions(self, rf):
        admin_user = UserFactory(first_name='admin', last_name='admin', is_superuser=True, is_staff=True)
        user = UserFactory(first_name='Bill', last_name='Smith')

        ApplicationFactory(name='app1')
        ApplicationFactory(name='app2', users=[user])

        request = rf.get(reverse('show-permissions-view', kwargs={'user_id': user.id}))
        request.user = admin_user

        response = ShowUserPermissionsView.as_view()(request, user_id=user.id)

        content = response.content.decode('utf-8')

        assert response.status_code == 200
        assert re.search(r'<td>app1</td>\n\s*<td>no</td>', content)
        assert re.search(r'<td>app2</td>\n\s*<td>yes</td>', content)


class TestUserAdmin:
    def test_get_fields_as_superuser(self, rf):
        user = UserFactory(is_staff=True, is_superuser=True)
        request = rf.get('/whatever/')
        request.user = user

        fields = set(UserAdmin(user.__class__, {}).get_fields(request, None))

        assert {'is_staff', 'is_superuser', 'groups', 'user_permissions'}.issubset(fields)

    def test_get_fields_not_as_superuser(self, rf):
        user = UserFactory(is_staff=True, is_superuser=False)
        request = rf.get('/whatever/')
        request.user = user

        fields = set(UserAdmin(user.__class__, {}).get_fields(request, None))

        assert {'is_staff', 'is_superuser', 'groups', 'user_permissions'}.isdisjoint(fields)


class TestAdminSSOLogin:
    def test_login_authenticated_but_not_staff_leads_to_403(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.get('/admin/login/')

        assert response.status_code == 403

    def test_login_authenticated_without_next_url_redirects_to_admin(self, client):
        user = UserFactory(is_staff=True)
        client.force_login(user)

        response = client.get('/admin/login/')

        assert response.status_code == 302
        assert response.url == '/admin/'

    def test_login_authenticated_redirects_to_next_url(self, client):
        user = UserFactory(is_staff=True)

        user.is_staff = True
        user.save()

        client.force_login(user)

        response = client.get('/admin/login/?next=/whatever/')

        assert response.status_code == 302
        assert response.url == '/whatever/'

    def test_login_redirects_to_sso_login(self, client):
        response = client.get('/admin/login/')

        assert response.status_code == 302
        assert response.url == reverse('saml2_login_start') + '?next=/admin/'


@pytest.fixture
def auth_client(client):
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(admin_user)

    return client


class TestMergeAction:
    def test_require_more_than_one_user(self, auth_client):
        """If only one checkbox is selected on the user's page then display an error, as we need at least
        two users to merge"""

        user = UserFactory()
        response = auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', 'select_across': 0, 'index': 0, '_selected_action': [user.id]},
            follow=True
        )

        assert b'<li class="error">You need to select at least two records to use the merge function</li>' in response.content  # noqa: E501

    def test_view_merge_form(self, auth_client):

        ids = [user.id for user in UserFactory.create_batch(2)]
        response = auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', 'select_across': 0, 'index': 0, '_selected_action': ids},
            follow=True
        )

        content = response.content.decode('utf-8')

        matches = re.findall(r'<input type="hidden" name="_selected_action" value="\d*">', content)
        assert set(matches) == set([f'<input type="hidden" name="_selected_action" value="{id}">' for id in ids])

        matches = re.findall(r'<input type="radio" name="merge-primary-id" value="\d*" required>', content)
        assert set(matches) == \
            set([f'<input type="radio" name="merge-primary-id" value="{id}" required>' for id in ids])

    def test_error_if_primary_user_not_selected(self, auth_client):
        """Check that an error is displayed if the user fails to select the primary user to merge into"""

        ids = [user.id for user in UserFactory.create_batch(2)]
        response = auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', '_selected_action': ids, 'post': 'yes'},
            follow=True
        )

        assert b'<li class="error">Specify a primary record.</li>' in response.content

    def test_successful_merge(self, auth_client):

        primary_user = UserFactory(email='primary@email.com', email_list=['primary2@email.com'])
        user2 = UserFactory(email='user2_1@email.com', email_list=['user2_2@email.com'])
        user3 = UserFactory(email='user3_1@email.com', email_list=['user3_2@email.com', 'user3_3@email.com'])

        ids = [primary_user.id, user2.id, user3.id]

        auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', '_selected_action': ids, 'merge-primary-id': primary_user.pk, 'post': 'yes'},
            follow=True
        )

        assert User.objects.filter(pk=primary_user.pk).exists()
        assert not User.objects.filter(pk__in=[user2.pk, user3.pk]).exists()

        all_emails = set([email.email for user in [primary_user, user2, user3] for email in user.emails.all()])

        primary_user.refresh_from_db()
        primary_emails = set(primary_user.emails.all().values_list('email', flat=True))

        assert primary_emails == all_emails

    def test_deleted_users_are_logged(self, auth_client):

        primary_user = UserFactory(email='primary@email.com')
        user2 = UserFactory(email='user2_1@email.com')

        ids = [primary_user.id, user2.id]

        assert LogEntry.objects.count() == 0

        auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', '_selected_action': ids, 'merge-primary-id': primary_user.pk, 'post': 'yes'},
            follow=True
        )

        assert LogEntry.objects.count() == 1
        log = LogEntry.objects.first()

        assert log.is_deletion()
        assert log.object_repr == f'User(id={user2.pk}, user_id={user2.user_id}, email_user_id={user2.email_user_id})'
        assert log.change_message == f'merged into {primary_user.user_id}'

    @pytest.mark.parametrize('perms,expected_status', [
        (
            [], 403
        ),
        (
            ['change_user'], 403
        ),
        (
            ['delete_user'], 403
        ),
        (
            ['delete_user', 'change_user'], 200
        ),
    ])
    def test_requires_change_and_delete_permissions(self, perms, expected_status, auth_client):
        assert User.objects.count() == 1
        user = User.objects.first()

        user.is_superuser = False
        user.save()

        for perm in perms:
            user.user_permissions.add(Permission.objects.get(codename=perm))

        ids = [user.id for user in UserFactory.create_batch(2)]
        response = auth_client.post(
            reverse('admin:user_user_changelist'),
            {'action': 'merge_users', '_selected_action': ids, 'merge-primary-id': ids[0], 'post': 'yes'},
            follow=True
        )

        assert response.status_code == expected_status
