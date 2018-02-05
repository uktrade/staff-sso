from django.contrib.auth import get_user_model

from sso.oauth2.models import Application


class UserDataExport:
    def __iter__(self):

        yield ['email', 'first_name', 'last_name', 'last login', 'other emails']

        for user in get_user_model().objects.all().order_by('email'):
            if user.last_login:
                last_login = user.last_login.strftime('%Y-%m-%d %H:%m:%S')
            else:
                last_login = ''

            row = [user.email, user.first_name, user.last_name, last_login]

            row.extend(user.emails.exclude(email=user.email).values_list('email', flat=True))

            yield row


class UserPermissionExport:
    """This will export a list of users: primary email, first name, last name, **all applications"""

    def get_application_list(self):
        applications = list(Application.objects.all().values_list('id', 'name'))
        self._app_ids, self._app_names = zip(*applications)

    def get_query(self):
        return get_user_model().objects.all().prefetch_related('permitted_applications').order_by('email')

    def get_header(self):
        return ['email', 'first_name', 'last_name'] + list(self._app_names)

    def get_user_application_columns(self, user):
        cols = []

        for app_id in self._app_ids:
            if user.permitted_applications.filter(pk=app_id).exists():
                cols.append('y')
            else:
                cols.append('')

        return cols

    def format_row(self, user):
        return [user.email, user.first_name, user.last_name] + self.get_user_application_columns(user)

    def __iter__(self):
        self.get_application_list()
        users = self.get_query()

        yield self.get_header()

        for user in users:
            yield self.format_row(user)
