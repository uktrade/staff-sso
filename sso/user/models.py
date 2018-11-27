from __future__ import unicode_literals
import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .managers import UserManager
from sso.oauth2.models import Application as OAuth2Application


class AccessProfile(models.Model):
    """This model defines a list of applications that a user can access"""
    name = models.CharField(
        _('name'),
        max_length=50,
    )

    description = models.TextField(
        _('description'),
        null=True,
        blank=True,
        help_text=_('for internal use only')
    )

    oauth2_applications = models.ManyToManyField(
        OAuth2Application,
        _('access_profiles'),
    )

    def __str__(self):
        return self.name

    def is_allowed(self, application: OAuth2Application):
        return application in self.oauth2_applications.all()


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _('email'), unique=True,
        help_text=_('Warning: editing this field may cause user profiles to break in Digital Workspace')
    )
    user_id = models.UUIDField(
        _('unique user id'), unique=True,
        default=uuid.uuid4
    )
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
        blank=True,
    )

    access_profiles = models.ManyToManyField(
        AccessProfile,
        related_name='users',
        blank=True,
    )

    last_accessed = models.DateTimeField(blank=True, null=True)

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

        if 'email' in kwargs:
            kwargs['email'] = kwargs['email'].lower()
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

    def _is_allowed_email(self, application):
        """Returns True if any of the user's emails are whitelisted in the OAuth2 app"""

        def _remove_username(email):
            return email.split('@')[1]

        if not application.allow_access_by_email_suffix:
            return False

        allowed_emails = {email.strip() for email in application.allow_access_by_email_suffix.split(',')}

        emails = self._get_domain_to_email_mapping().keys()

        return not allowed_emails.isdisjoint(emails)

    def _get_domain_to_email_mapping(self):
        """Return a dictionary of a user's emails and the domain, e.g. `{domain: email}` """

        def _remove_username(email):
            return email.split('@')[1]

        return {
            _remove_username(email): email for email in self.emails.all().values_list('email', flat=True)
        }

    def can_access(self, application: OAuth2Application):
        """ Can the user access this application?"""

        # does the application grant access?
        if application.default_access_allowed or self._is_allowed_email(application):
            return True

        # is the user permitted to access the application directly?
        if application in self.permitted_applications.all():
            return True

        # is the user granted access by an access profile?
        for profile in self.access_profiles.all():
            if profile.is_allowed(application):
                return True

        return False

    def get_emails_for_application(self, application):
        """
        Get all emails for current Oauth2 application and return a tuple (primary_email, related_emails)
        """

        if not application or application.provide_immutable_email:
            return self.email, list(self.emails.exclude(email=self.email).values_list('email', flat=True))

        emails = self._get_domain_to_email_mapping()

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

    def get_application_username(self, application=None):
        """
        :param application:  application or None
        :return:  result of get_emails_for_application or get_username if application is None
        """
        if application is None:
            return self.get_username()
        else:
            return self.get_emails_for_application(application)[0]


class EmailAddress(models.Model):
    user = models.ForeignKey(User, related_name='emails', on_delete=models.CASCADE)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        """
        Ensure that emails are lower cased
        """

        self.email = self.email.lower()

        return super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'email addresses'
