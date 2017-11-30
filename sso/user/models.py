from __future__ import unicode_literals
import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _('email'), unique=True
    )

    account_ref = models.UUIDField(
        _('Unique account reference'),
        default=uuid.uuid4, editable=False)

    first_name = models.CharField(
        _('first name'), max_length=50, blank=True
    )
    last_name = models.CharField(
        _('last name'), max_length=50, blank=True
    )

    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now,
    )
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user can log into the admin area and assign users to groups.'
        ),
    )
    permitted_applications = models.ManyToManyField(
        settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
        related_name='users',
        help_text=_(
            'Applications that this user is permitted to access'
        ),
        blank=True
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_superuser

    def save(self, *args, **kwargs):
        """
        Ensure that emails are lower cased and that the primary email address
        exists in the fk'd EmailAddress model
        """

        self.email = self.email.lower()

        return_value = super().save(*args, **kwargs)

        if not self.emails.filter(email=self.email).exists():
            self.emails.create(email=self.email)

        return return_value

    def get_full_name(self):
        """
        Django method that must be implemented

        Return first name / last name if not empty or email otherwise
        """
        names = [name for name in [self.first_name, self.last_name] if name]
        if names:
            return ' '.join(names)
        return self.email

    def get_short_name(self):
        """Django method that must be implemented"""
        return self.get_full_name()

    def can_access(self, application):
        """Can this user access the application?"""
        return application.default_access_allowed or application in self.permitted_applications.all()

    def get_emails_for_application(self, application):
        """
        Get all emails for current Oauth2 application and return a tuple (primary_email, related_emails)
        """

        def _remove_username(email):
            return email.split('@')[1]

        emails = {
            _remove_username(email): email for email in self.emails.all().values_list('email', flat=True)
        }

        if not emails:
            return self.email, []

        for domain in application.get_email_order():
            if domain in emails:
                primary_email = emails.pop(domain)
                break
        else:
            # Do we need to be more consistent here? Perhaps returning user.email instead?
            # or is this an edge case?
            _, primary_email = emails.popitem()

        return primary_email, emails.values()


class EmailAddress(models.Model):
    user = models.ForeignKey(User, related_name='emails')
    email = models.EmailField(unique=True)

    class Meta:
        verbose_name_plural = 'email addresses'
