from django.contrib.auth import get_user_model


class UserDataExport:
    def __iter__(self):

        yield ['user_id', 'email', 'first_name', 'last_name', 'last login', 'last accessed', 'other emails']

        for user in get_user_model().objects.all().order_by('email'):
            if user.last_login:
                last_login = user.last_login.strftime('%Y-%m-%d %H:%m:%S')
            else:
                last_login = ''

            if user.last_accessed:
                last_accessed = user.last_accessed.strftime('%Y-%m-%d %H:%m:%S')
            else:
                last_accessed = ''

            row = [user.user_id, user.email, user.first_name, user.last_name, last_login, last_accessed]

            row.extend(user.emails.exclude(email=user.email).values_list('email', flat=True))

            yield row
