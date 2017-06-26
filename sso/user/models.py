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
        # django method that must be implemented
        return self.email

    def get_short_name(self):
        # django method that must be implemented
        return self.email
