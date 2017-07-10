from __future__ import unicode_literals

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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_superuser

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
