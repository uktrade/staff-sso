import urllib.parse

from sso.emailauth.models import EmailToken

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse


class Command(BaseCommand):
    help = "Get a one-time authenticate url to impersonate an SSO user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            dest="user_email",
            help="The email of the user you want to impersonate. A user with this email must already exist",
        )

    def handle(self, *args, user_email, **kwargs):

        User = get_user_model()

        # verify that the user exists in the DB
        try:
            User.objects.get_by_email(user_email)
        except User.DoesNotExist:
            self.stdout.write("User %s does not exist", user_email)
            return 1

        token = EmailToken.objects.create_token(user_email)

        path = reverse("emailauth:email-auth-signin", kwargs=dict(token=token))

        return urllib.parse.urljoin(settings.BASE_URL, path)
