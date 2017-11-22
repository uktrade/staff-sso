import pytest
from django.core.exceptions import ValidationError

from sso.user.data_import import UserImport
from sso.user.models import User
from .factories.user import UserFactory
from .factories.oauth import ApplicationFactory


pytestmark = [
    pytest.mark.django_db
]


class TestUserImport:
    def test_extract_row_data_valid_data(self):
        row = ['John', 'Smith', '', 'test@aaa.com', '', 'test@bbb.com', '', 'test@ccc.com', '', '', '', '']

        first_name, last_name, emails = UserImport(None, None)._extract_row_data(row)

        assert first_name == 'John'
        assert last_name == 'Smith'
        assert emails == ['test@aaa.com', 'test@bbb.com', 'test@ccc.com']

    def test_extract_row_data_missing_first_name(self):
        row = ['', 'Smith', 'test@test.com']

        with pytest.raises(ValidationError):
            UserImport(None, None)._extract_row_data(row)

    def test_extract_row_data_missing_first_no_emails(self):
        row = ['John', 'Smith', '']

        with pytest.raises(ValidationError):
            UserImport(None, None)._extract_row_data(row)

    def test_extract_row_data_missing_first_invalid_emails(self):
        row = ['John', 'Smith', 'not-an-email']

        with pytest.raises(ValidationError):
            UserImport(None, None)._extract_row_data(row)

    def test_extract_row_data_lower_cases_emails(self):
        row = ['John', 'Smith', ' UPPERCASE@EMAIL.COM ']

        _, _, emails = UserImport(None, None)._extract_row_data(row)

        assert emails[0] == 'uppercase@email.com'

    def test_order_emails(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        ordered_emails = UserImport(None, None)._order_emails(['test@fff.com', 'test@bbb.com', 'test@ccc.com'])

        assert ordered_emails == ['test@bbb.com', 'test@ccc.com', 'test@fff.com']

    def test_order_users(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])
        user3 = UserFactory(email='test@aaa.com')

        users = UserImport(None, None)._order_users([user1, user2, user3])

        assert users == [user3, user1, user2]

    def test_order_users_no_default_ordering(self, settings):
        settings.DEFAULT_EMAIL_ORDER = ''

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])

        users = UserImport(None, None)._order_users([user1, user2])

        assert set(users) == set([user1, user2])

    def test_find_associated_users_orders_users(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])
        user3 = UserFactory(email='test@aaa.com')

        users = UserImport(None, None)._find_associated_users(['test@aaa.com', 'test@zzz.com', 'test@qqq.com'])

        assert users == [user3, user1, user2]

    def test_find_associated_users(self):
        user1 = UserFactory(email='test@aaa.com', email_list=['test@bbb.com'])
        user2 = UserFactory(email='test@ccc.com')
        user3 = UserFactory(email='test@ddd.com')
        user4 = UserFactory(email='test@eee.com', email_list=['test@fff.com', 'test@ggg.com'])

        users = UserImport(None, None)._find_associated_users(['test@aaa.com', 'test@ddd.com', 'test@fff.com'])

        assert set(users) == set([user1, user3, user4])

    def test_find_associated_users_dedupes_users(self):
        pass

    def test_update_user(self):
        user = UserFactory(
            first_name='Steve',
            last_name='White',
            email='test@zzz.com',
            email_list=['test@ddd.com', 'test@vvv.com']
        )

        app1 = ApplicationFactory()
        app2 = ApplicationFactory(users=[user])

        UserImport(None, [app1.id])._update_user(
            user,
            'Bill',
            'Smith',
            'primary@email.com',
            ['test@aaa.com', 'test@bbb.com', 'test@ccc.com'])

        user = User.objects.first()

        assert User.objects.count() == 1
        assert user.first_name == 'Bill'
        assert user.last_name == 'Smith'
        assert user.email == 'primary@email.com'
        assert user.emails.count() == 4
        assert set(user.emails.all().values_list('email', flat=True)) == set(['test@aaa.com', 'test@bbb.com', 'test@ccc.com', 'primary@email.com'])
        assert user.permitted_applications.count() == 1
        assert user.permitted_applications.first().id == app1.id

    def test_process_invalid_csv_row(self):
        csv = [
            ['first', 'last', 'not-an-email']
        ]

        user_import = UserImport(csv, [1])
        user_import.process()

        assert User.objects.count() == 0
        assert user_import.get_stats()['rows_failed'] == 1
        assert user_import.get_stats()['rows_imported'] == 0
        assert user_import.get_stats()['users_created'] == 0

    def test_process_new_user(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        csv = [
            ['first', 'last', '', 'test@zzz.com', 'test@nnn.com', '', '', '', 'test@ccc.com']
        ]

        app = ApplicationFactory()

        user_import = UserImport(csv, [app.id])
        user_import.process()

        user = User.objects.first()

        assert User.objects.count() == 1
        assert user_import.get_stats()['rows_failed'] == 0
        assert user_import.get_stats()['rows_imported'] == 1
        assert user_import.get_stats()['users_created'] == 1
        assert user.email == 'test@ccc.com'
        assert set(user.emails.all().values_list('email', flat=True)) == set(['test@zzz.com', 'test@nnn.com', 'test@ccc.com'])
        assert user.first_name == 'first'
        assert user.last_name == 'last'

    def test_process_existing_user(self):
        pass

    def test_process_dry_run_is_none_destructive(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        csv = [
            ['first', 'last', '', 'test@zzz.com', 'test@nnn.com', '', '', '', 'test@ccc.com']
        ]

        app = ApplicationFactory()

        user_import = UserImport(csv, [app.id])
        user_import.process(dry_run=True)

        assert User.objects.count() == 0

    def test_process_determines_correct_primary_user_and_removes_other_users(self, settings):

        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        csv = [
            ['first', 'last', '', 'test@bbb.com', '', 'test@ccc.com', '', 'test@ddd.com']
        ]

        user1 = UserFactory(email='test@nnn.com', email_list=['test@ccc.com'])
        user2 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com'])
        user3 = UserFactory(email='test@qqq.com', email_list=['test@ddd.com'])
        user4 = UserFactory(email='test@unrelated.com')

        app = ApplicationFactory()

        user_import = UserImport(csv, [app.id])
        user_import.process()

        # user2 should be primary
        # user1 & user3 should be deleted
        # user4 is unrelated and should be untouched

        assert user_import.get_stats()['users_created'] == 0
        assert user_import.get_stats()['users_deleted'] == 2
        assert user_import.get_stats()['users_updated'] == 1
        assert user_import.get_stats()['rows_imported'] == 1

        assert User.objects.count() == 2
        user = User.objects.exclude(email='test@unrelated.com').first()
        assert user == user2
        assert user.email == 'test@bbb.com'
        assert set(user.emails.all().values_list('email', flat=True)) == \
               set(['test@bbb.com', 'test@ccc.com', 'test@ddd.com'])


class TestAdminImportView:
    def test_csv_import_dry_run(self):
        # TODO
        pass

    def test_csv_import(self):
        # TODO
        pass