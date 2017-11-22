from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class UserImport:

    def __init__(self, csv_reader, applications):
        self.csv = csv_reader
        self.applications = applications

        self._valid_email = EmailValidator('An email is invalid')

        self.logs = []

        # stats
        self.rows_imported = 0
        self.rows_failed = 0
        self.users_created = 0
        self.users_updated = 0
        self.users_deleted = 0

    def log(self, message):
        self.logs.append(message)

    def get_stats(self):
        return OrderedDict([
            ('rows_imported', self.rows_imported),
            ('rows_failed', self.rows_failed),
            ('users_created', self.users_created),
            ('users_updated', self.users_updated),
            ('users_deleted', self.users_deleted)
        ])

    def _extract_row_data(self, row):
        """
        Returns a tuple containing: (first_name, last_name, emails)
        """

        first_name, last_name, *cols = row

        emails = [col.strip().lower() for col in cols if col]

        if not first_name or not last_name:
            raise ValidationError('Missing first or last name')

        if not emails:
            raise ValidationError('No emails provided')

        for email in emails:
            try:
                self._valid_email(email)
            except ValidationError:
                raise ValidationError(f'{email} is not valid')

        return first_name, last_name, self._order_emails(emails)

    def _order_emails(self, emails):
        ordering = [email.strip() for email in settings.DEFAULT_EMAIL_ORDER.split(',')]

        def _remove_username(email):
            return email.split('@')[1]

        ordered_emails = []

        for domain in ordering:
            for email in emails:
                if domain == _remove_username(email):
                    ordered_emails.append(email)
                    emails.pop(emails.index(email))

                    break

        return ordered_emails + emails

    def _order_users(self, users):
        """Take a list of users and order by settings.DEFAULT_EMAIL_ORDER"""

        users = list(users)

        ordering = [email.strip() for email in settings.DEFAULT_EMAIL_ORDER.split(',')]

        if not ordering:
            return users

        ordered_users = []

        for domain in ordering:
            for user in users:
                if user.emails.filter(email__endswith=domain).exists():
                    ordered_users.append(user)
                    users.pop(users.index(user))

                    break

        return ordered_users + users

    def _find_associated_users(self, emails):
        """
        Get all user entries the user has for all of their email aliases and return a list ordered by
        settings.DEFAULT_EMAIL_ORDER
        """

        users = []

        for email in emails:
            try:
                user = User.objects.get_by_email(email)
                if user not in users:
                    users.append(user)
            except User.DoesNotExist:
                pass

        return self._order_users(users)

    def _update_user(self, user, first_name, last_name, primary_email, related_emails):
        """Set permissions and first/last name"""

        # This must happen first as user.save() adds user.email to user.email_list
        user.emails.all().delete()

        user.first_name = first_name
        user.last_name = last_name
        user.email = primary_email

        user.save()

        user.permitted_applications.clear()
        user.permitted_applications.add(*self.applications)

        for email in related_emails:
            user.emails.create(email=email)

    def process(self, dry_run=False):
        """
        Process the csv
        """

        for i, row in enumerate(self.csv):

            self.log(f'------ row {i+1} -------')

            try:
                first_name, last_name, emails = self._extract_row_data(row)
            except ValidationError as ex:
                self.log(f'skipping row due to validation error: {ex}')

                self.rows_failed += 1

                continue

            existing_users = self._find_associated_users(emails)
            primary_email, *related_emails = emails

            self.log('found {} users: {}'.format(
                len(existing_users),
                ', '.join(user.email for user in existing_users)
            ))

            self.log('primary email: {} / related emails: {}'.format(
                primary_email,
                ', '.join(related_emails)
            ))

            if not existing_users:
                self.log(f'creating a new user')

                self.users_created += 1

                if not dry_run:
                    primary_user = User.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        email=primary_email
                    )

            else:
                self.log('updating user')
                self.users_updated += 1
                primary_user, *other_users = existing_users

                if other_users:
                    self.log('deleting {} other users'.format(len(other_users)))

                    self.users_deleted += len(other_users)

                    if not dry_run:
                        for user in other_users:
                            user.delete()

            self.rows_imported += 1

            if not dry_run:
                self._update_user(primary_user, first_name, last_name, primary_email, related_emails)
