from django.db import models
from django.utils.translation import ugettext_lazy as _

from oauth2_provider.models import AbstractApplication


class Application(AbstractApplication):
    default_access_allowed = models.BooleanField(
        _('default access allowed'),
        default=False,
        help_text=_(
            'Allow all authenticated users to access this application'
        )
    )
