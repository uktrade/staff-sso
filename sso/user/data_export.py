from django.contrib.auth import get_user_model


class UserDataExport:
    def __iter__(self):

        yield ['user_id', 'email', 'first_name', 'last_name', 'last login', 'last accessed', 'other emails',
               'access profiles', 'permitted apps']

        for user in get_user_model().objects.all().order_by('email'):
            if user.last_login:
                last_login = user.last_login.strftime('%Y-%m-%d %H:%m:%S')
            else:
                last_login = ''

            if user.last_accessed:
                last_accessed = user.last_accessed.strftime('%Y-%m-%d %H:%m:%S')
            else:
                last_accessed = ''

            other_emails = '|'.join(user.emails.exclude(email=user.email).values_list('email', flat=True))
            access_profiles = '|'.join(ap.slug for ap in user.access_profiles.all())
            permitted_applications = '|'.join(pa.name for pa in user.permitted_applications.all())
            row = [user.user_id, user.email, user.first_name, user.last_name, last_login, last_accessed, other_emails,
                   access_profiles, permitted_applications]

            yield row
