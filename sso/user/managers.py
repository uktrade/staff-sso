import logging

from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_superuser", True)

        return self._create_user(email, password, **extra_fields)

    def get_or_create(self, defaults=None, **kwargs):
        """
        Look up an object with the given kwargs, creating one if necessary.
        Return a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        # The get() needs to be targeted at the write database in order
        # to avoid potential transaction consistency problems.

        self._for_write = True

        defaults = defaults or {}
        email = kwargs["email"].lower()
        params = {**defaults, "email": email}

        try:
            user, created = self.get_by_email(email), False
        except self.model.DoesNotExist:
            user, created = self.create(**params), True

        return user, created

    def get_by_email(self, email):
        email = email.lower()
        try:
            return self.get(emails__email=email)
        except self.model.DoesNotExist:
            return self.get(email=email)

    def set_email_last_login_time(self, email):
        from sso.user.models import EmailAddress

        email_obj = EmailAddress.objects.get(email=email.lower())
        email_obj.last_login = timezone.now()
        email_obj.save()
