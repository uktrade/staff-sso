import datetime as dt
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from sso.user.models import User


def generate_token():
    return secrets.token_hex(32)


class EmailTokenManager(models.Manager):
    def create_token(self, email):
        """generate EmailToken object and return the token"""

        obj = EmailToken()
        obj.email = email
        obj.extract_name_from_email(email)
        obj.save()

        return obj.token


class EmailToken(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=128, default=generate_token, unique=True)
    email = models.EmailField()
    used = models.BooleanField(default=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    objects = EmailTokenManager()

    @property
    def is_expired(self):
        return timezone.now() > self.created + dt.timedelta(seconds=settings.EMAIL_TOKEN_TTL)

    def extract_name_from_email(self, email):
        """Attempt to populate the first and last name fields from the user's email"""

        username = email.split('@')[0]
        parts = username.split('.')
        self.first_name = parts[0]
        self.last_name = ' '.join(parts[1:])

    def get_user(self):

        defaults = {
            'first_name': self.first_name,
            'last_name': self.last_name
        }

        user, _ = User.objects.get_or_create(email=self.email, defaults=defaults)

        return user

    def mark_used(self):
        self.used = True
        self.save()
