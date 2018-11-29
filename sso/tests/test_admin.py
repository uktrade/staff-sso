import re
import pytest

from django.shortcuts import reverse

from sso.user.admin_views import ShowUserPermissionsView

from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory
from django.contrib.auth.models import AnonymousUser


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
        admin_user = UserFactory(is_superuser=True)
        user = UserFactory(first_name='Bill', last_name='Smith')

        request = rf.get(reverse('show-permissions-view', kwargs={'user_id': user.id}))
        request.user = admin_user

        response = ShowUserPermissionsView.as_view()(request, user_id=user.id)

        content = response.content.decode('utf-8')

        assert response.status_code == 200
        assert 'User: {}'.format(user.get_full_name()) in content

    def test_application_permissions(self, rf):
        admin_user = UserFactory(first_name='admin', last_name='admin', is_superuser=True)
        user = UserFactory(first_name='Bill', last_name='Smith')

        app1 = ApplicationFactory(name='app1')
        app2 = ApplicationFactory(name='app2', users=[user])

        request = rf.get(reverse('show-permissions-view', kwargs={'user_id': user.id}))
        request.user = admin_user

        response = ShowUserPermissionsView.as_view()(request, user_id=user.id)

        content = response.content.decode('utf-8')

        assert response.status_code == 200
        assert re.search(r'<td>app1</td>\n\s*<td>no</td>', content)
        assert re.search(r'<td>app2</td>\n\s*<td>yes</td>', content)


