import pytest

from django.core.exceptions import ValidationError

from sso.user.data_import import UserAliasImport, UserMergeImport
from sso.user.models import User
from .factories.oauth import ApplicationFactory
from .factories.user import UserFactory

pytestmark = [
    pytest.mark.django_db
]


class TestUserMergeImport:
    def test_extract_row_data_valid_data(self):
        row = ['John', 'Smith', '', 'test@aaa.com', '', 'test@bbb.com', '', 'test@ccc.com', '', '', '', '']

        first_name, last_name, emails = UserMergeImport(None, None)._extract_row_data(row)

        assert first_name == 'John'
        assert last_name == 'Smith'
        assert emails == ['test@aaa.com', 'test@bbb.com', 'test@ccc.com']

    @pytest.mark.parametrize(
        'row', (
            ['', 'Smith', 'test@test.com'],
            ['John', 'Smith', ''],
            ['John', 'Smith', 'not-an-email']
        )
    )
    def test_extract_row_data_invalid_data(self, row):
        with pytest.raises(ValidationError):
            UserMergeImport(None, None)._extract_row_data(row)

    def test_extract_row_data_lower_cases_emails(self):
        row = ['John', 'Smith', ' UPPERCASE@EMAIL.COM ']

        _, _, emails = UserMergeImport(None, None)._extract_row_data(row)

        assert emails[0] == 'uppercase@email.com'

    def test_order_emails(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        ordered_emails = UserMergeImport(None, None)._order_emails(['test@fff.com', 'test@bbb.com', 'test@ccc.com'])

        assert ordered_emails == ['test@bbb.com', 'test@ccc.com', 'test@fff.com']

    def test_order_users(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])
        user3 = UserFactory(email='test@aaa.com')

        users = UserMergeImport(None, None)._order_users([user1, user2, user3])

        assert users == [user3, user1, user2]

    def test_order_users_no_default_ordering(self, settings):
        settings.DEFAULT_EMAIL_ORDER = ''

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])

        users = UserMergeImport(None, None)._order_users([user1, user2])

        assert set(users) == set([user1, user2])

    def test_find_associated_users_orders_users(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        user1 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com', 'test@ccc.com'])
        user2 = UserFactory(email='test@qqq.com', email_list=['test@iii.com', 'test@vvv.com'])
        user3 = UserFactory(email='test@aaa.com')

        users = UserMergeImport(None, None)._find_associated_users(['test@aaa.com', 'test@zzz.com', 'test@qqq.com'])

        assert users == [user3, user1, user2]

    def test_find_associated_users(self):
        user1 = UserFactory(email='test@aaa.com', email_list=['test@bbb.com'])
        user2 = UserFactory(email='test@ccc.com')  # noqa: F841
        user3 = UserFactory(email='test@ddd.com')
        user4 = UserFactory(email='test@eee.com', email_list=['test@fff.com', 'test@ggg.com'])

        users = UserMergeImport(None, None)._find_associated_users(['test@aaa.com', 'test@ddd.com', 'test@fff.com'])

        assert set(users) == set([user1, user3, user4])

    def test_find_associated_users_dedupes_users(self):
        """
        Ensure there are no duplicate users in the returned list
        """
        user = UserFactory(email='test@aaa.com', email_list=['test@bbb.com'])

        users = UserMergeImport(None, None)._find_associated_users(['test@aaa.com', 'test@bbb.com'])

        assert users == [user]

    def test_update_user(self):
        user = UserFactory(
            first_name='Steve',
            last_name='White',
            email='primary@email.com',
            email_list=['test@ddd.com', 'test@vvv.com']
        )

        app1 = ApplicationFactory()
        app2 = ApplicationFactory(users=[user])  # noqa: F841

        form_data = dict(applications=[app1.id])

        UserMergeImport(None, form_data)._update_user(
            user,
            'Bill',
            'Smith',
            ['primary@email.com', 'test@aaa.com', 'test@bbb.com', 'test@ccc.com'])

        user = User.objects.first()

        assert User.objects.count() == 1
        assert user.first_name == 'Bill'
        assert user.last_name == 'Smith'
        assert user.email == 'primary@email.com'
        assert user.emails.count() == 4
        assert set(user.emails.all().values_list('email', flat=True)) == \
            set(['test@aaa.com', 'test@bbb.com', 'test@ccc.com', 'primary@email.com'])
        assert user.permitted_applications.count() == 1
        assert user.permitted_applications.first().id == app1.id

    def test_process_invalid_csv_row(self):
        csv = [
            ['first', 'last', 'not-an-email']
        ]

        form_data = dict(applications=[1])

        user_import = UserMergeImport(csv, form_data)
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

        form_data = dict(applications=[app.id])

        user_import = UserMergeImport(csv, form_data)
        user_import.process()

        user = User.objects.first()

        assert User.objects.count() == 1
        assert user_import.get_stats()['rows_failed'] == 0
        assert user_import.get_stats()['rows_imported'] == 1
        assert user_import.get_stats()['users_created'] == 1
        assert user.email == 'test@ccc.com'
        assert set(user.emails.all().values_list('email', flat=True)) == \
            set(['test@zzz.com', 'test@nnn.com', 'test@ccc.com'])
        assert user.first_name == 'first'
        assert user.last_name == 'last'

    def test_process_dry_run_is_non_destructive(self, settings):
        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        csv = [
            ['first', 'last', '', 'test@zzz.com', 'test@nnn.com', '', '', '', 'test@ccc.com']
        ]

        app = ApplicationFactory()

        form_data = dict(applications=[app.id])

        user_import = UserMergeImport(csv, form_data)
        user_import.process(dry_run=True)

        assert User.objects.count() == 0

    def test_process_determines_correct_primary_user_and_removes_other_users(self, settings):

        settings.DEFAULT_EMAIL_ORDER = 'aaa.com, bbb.com, ccc.com'

        csv = [
            ['first', 'last', '', 'test@bbb.com', '', 'test@ccc.com', '', 'test@ddd.com']
        ]

        user1 = UserFactory(email='test@nnn.com', email_list=['test@ccc.com'])  # noqa: F841
        user2 = UserFactory(email='test@zzz.com', email_list=['test@bbb.com'])
        user3 = UserFactory(email='test@qqq.com', email_list=['test@ddd.com'])  # noqa: F841
        user4 = UserFactory(email='test@unrelated.com')  # noqa: F841

        app = ApplicationFactory()

        form_data = dict(applications=[app.id])

        user_import = UserMergeImport(csv, form_data)
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
        assert user.email == 'test@zzz.com'
        assert set(user.emails.all().values_list('email', flat=True)) == \
            set(['test@zzz.com', 'test@bbb.com', 'test@ccc.com', 'test@ddd.com'])

    def test_process_does_not_change_primary_email_for_existing_users(self):
        """
        The primary email address `user.email` is an immutable key and must not be
        modified.
        """

        csv = [
            ['first', 'last', '', 'test@bbb.com', '', 'test@ccc.com', '', 'test@ddd.com']
        ]

        UserFactory(email='test@nnn.com', email_list=['test@ccc.com'])  # noqa: F841
        app = ApplicationFactory(email_ordering='aaa.com, bbb.com, ccc.com')

        form_data = dict(applications=[app.id])

        user_import = UserMergeImport(csv, form_data)
        user_import.process()

        assert user_import.get_stats()['users_created'] == 0
        assert user_import.get_stats()['users_deleted'] == 0
        assert user_import.get_stats()['users_updated'] == 1
        assert user_import.get_stats()['rows_imported'] == 1

        user = User.objects.first()
        assert user.email == 'test@nnn.com'
        assert set(user.emails.all().values_list('email', flat=True)) == \
            set(['test@nnn.com', 'test@bbb.com', 'test@ccc.com', 'test@ddd.com'])


class TestUserAliasImport:
    def test_invalid_csv_data(self):

        csv = [
            ['not-an-email', 'test@test.com'],
            ['test@test.com', 'test@test.com', 'too-many-rows']
        ]

        user_import = UserAliasImport(csv)
        user_import.process()

        assert user_import.get_stats()['rows_skipped'] == 2

    def test_dry_run_does_not_change_data(self):
        user = UserFactory(email='test@test.com', email_list=['test2@test.com'])

        csv = [
            ['test@test.com', 'test3@test.com']
        ]

        user_import = UserAliasImport(csv)
        user_import.process(dry_run=True)

        assert user_import.get_stats()['rows_processed'] == 1
        assert not user.emails.filter(email='test3@test.com').exists()

    def test_no_existing_user(self):
        """Do nothing if we don't have an existing user"""

        csv = [
            ['test@test.com', 'test3@test.com']
        ]

        user_import = UserAliasImport(csv)
        user_import.process()

        assert user_import.get_stats()['rows_skipped'] == 1
        assert User.objects.count() == 0

    def test_duplicate_user_fails(self):
        """Do nothing if there are multiple user records"""
        UserFactory(email='test@test.com')
        UserFactory(email='test2@test.com')

        csv = [
            ['test@test.com', 'test2@test.com']
        ]

        user_import = UserAliasImport(csv)
        user_import.process(dry_run=True)

        assert user_import.get_stats()['rows_skipped'] == 1

    def test_alias_exists(self):
        """Nothing to do if there alias already exists"""
        UserFactory(email='test@test.com', email_list=['test2@test.com'])

        csv = [
            ['test@test.com', 'test2@test.com']
        ]

        user_import = UserAliasImport(csv)
        user_import.process(dry_run=True)

        assert user_import.get_stats()['rows_skipped'] == 1

    def test_alias_added_success(self):
        user = UserFactory(email='test@test.com', email_list=['test2@test.com'])

        csv = [
            ['test@test.com', 'test3@test.com']
        ]

        user_import = UserAliasImport(csv)
        user_import.process()

        assert user_import.get_stats()['rows_processed'] == 1
        assert user.emails.filter(email='test3@test.com').exists()
