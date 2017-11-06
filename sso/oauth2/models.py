from django.db import models
from django.utils.translation import ugettext_lazy as _

from oauth2_provider.models import AbstractApplication


class Application(AbstractApplication):
    default_access = models.BooleanField(
        _('default access'),
        default=False,
        help_text=_(
            'Allow all authenticated users to access this application'
        )
    )
