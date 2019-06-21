import re

import pytest

from django.contrib.auth.models import AnonymousUser
from django.shortcuts import reverse

from sso.user.admin_views import ShowUserPermissionsView
from sso.user.admin import UserAdmin

from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory


pytestmark = [
    pytest.mark.django_db
]


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
        assert response.url == '/saml2/login/?next=/admin/'
