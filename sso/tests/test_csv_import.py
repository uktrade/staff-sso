from io import StringIO
import csv

from sso.user.admin_views import AdminUserImportView
from sso.user.models import User
from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory


import pytest

pytestmark = [
    pytest.mark.django_db
]

class TestAdminUserImportView:
    def test_process_row_new_user(self):
        """Test `process_row()` adds a new user"""

        assert User.objects.count() == 0

        application = ApplicationFactory()

        view = AdminUserImportView()

        row = [
            'test@test.com',
            'Mike',
            'Smith'
        ]

        view._process_row(row, [application.id], [], False)

        assert User.objects.count() == 1

        user = User.objects.first()

        assert user.first_name == 'Mike'
        assert user.last_name == 'Smith'
        assert user.email == 'test@test.com'
        assert user.permitted_applications.count() == 1
        assert user.permitted_applications.first().id == application.id

    def test_process_row_new_user_email_is_lowercase(self):
        """Test `process_row()` lowercases emails"""
        assert User.objects.count() == 0

        application = ApplicationFactory()

        view = AdminUserImportView()

        row = [
            'TEST@TEST.COM',
            'Mike',
            'Smith'
        ]

        view._process_row(row, [application.id], [], False)

        assert User.objects.count() == 1

        user = User.objects.first()

        assert user.email == 'test@test.com'

    def test_process_csv_new_entries(self):
        """A basic test of `process_csv()` with new users"""
        data = StringIO(
"""joe@smith.com,joe,smith
jim@smith.com,jim,smith
smith@joe.com,smith,joe
hello.world@world.com,hello,world
doctor.strange@world.com,dr,strange""")

        application1 = ApplicationFactory()
        application2 = ApplicationFactory()

        csv_reader = csv.reader(data)

        view = AdminUserImportView()

        assert User.objects.count() == 0

        output = view._process_csv(csv_reader, [application1.id], [], False)

        assert User.objects.count() == 5

        for user in User.objects.all():
            apps = user.permitted_applications.all()
            assert apps.count() == 1
            assert apps[0].id == application1.id

    def test_process_csv_some_existing_entries(self):
        """A basic test of `process_csv()` with some existing users"""
        user1 = UserFactory(email='joe@smith.com')
        user2 = UserFactory(email='doctor.strange@world.com')

        data = StringIO(
"""joe@smith.com,joe,smith
jim@smith.com,jim,smith
smith@joe.com,smith,joe
hello.world@world.com,hello,world
doctor.strange@world.com,dr,strange""")

        application1 = ApplicationFactory()
        application2 = ApplicationFactory(users=[user1, user2])

        csv_reader = csv.reader(data)

        view = AdminUserImportView()

        assert User.objects.count() == 2

        output = view._process_csv(csv_reader, [application1.id], [], False)

        assert User.objects.count() == 5

    def test_process_row_existing_user_add_perms_exists(self):
        user = UserFactory(email='joe@smith.com')

        application = ApplicationFactory(users=[user])

        row = [
            'joe@smith.com',
            'Joe',
            'Smith'
        ]

        view = AdminUserImportView()
        view._process_row(row, [], [application.id], True)

        assert user.permitted_applications.count() == 1
        assert user.permitted_applications.all()

    def test_process_row_existing_user_add_perms(self):
        user = UserFactory(email='joe@smith.com')

        application = ApplicationFactory()
        application2 = ApplicationFactory(users=[user])

        row = [
            'joe@smith.com',
            'Joe',
            'Smith'
        ]

        view = AdminUserImportView()
        view._process_row(row, [], [application.id], True)

        assert user.permitted_applications.count() == 2

    def test_process_row_existing_user_remove_perms(self):
        user = UserFactory(email='joe@smith.com')

        application = ApplicationFactory(users=[user])

        assert user.permitted_applications.count() == 1

        row = [
            'joe@smith.com',
            'Joe',
            'Smith'
        ]

        view = AdminUserImportView()
        view._process_row(row, [], [application.id], False)

        assert user.permitted_applications.count() == 0
