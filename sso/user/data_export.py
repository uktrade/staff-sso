from django.contrib.auth import get_user_model

from sso.user.models import EmailAddress


class UserDataExport:
    def __iter__(self):

        yield [
            "user_id",
            "email_user_id",
            "contact_email",
            "email",
            "first_name",
            "last_name",
            "date joined",
            "last login",
            "last accessed",
            "access profiles",
            "permitted apps",
            "other emails",
        ]

        for user in get_user_model().objects.all().order_by("email"):
            if user.last_login:
                last_login = user.last_login.strftime("%Y-%m-%d %H:%m:%S")
            else:
                last_login = ""

            if user.last_accessed:
                last_accessed = user.last_accessed.strftime("%Y-%m-%d %H:%m:%S")
            else:
                last_accessed = ""

            date_joined = user.date_joined.strftime("%Y-%m-%d %H:%m:%S")

            other_emails = user.emails.exclude(email=user.email).values_list("email", flat=True)
            access_profiles = "|".join(ap.slug for ap in user.access_profiles.all())
            permitted_applications = "|".join(pa.name for pa in user.permitted_applications.all())
            row = [
                user.user_id,
                user.email_user_id,
                user.contact_email,
                user.email,
                user.first_name,
                user.last_name,
                date_joined,
                last_login,
                last_accessed,
                access_profiles,
                permitted_applications,
                *other_emails,
            ]

            yield row


class EmailLastLoginExport:
    def __iter__(self):

        yield ["email", "last login"]

        for email in EmailAddress.objects.all().order_by("-last_login"):
            if email.last_login:
                last_login = email.last_login.strftime("%Y-%m-%d %H:%m:%S")
            else:
                last_login = ""

            row = [email.email, last_login]

            yield row
