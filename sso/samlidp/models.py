import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from sso.core.ip_filter import get_client_ip

logger = logging.getLogger(__file__)

from djangosaml2idp.models import AbstractServiceProvider


class SamlApplication(AbstractServiceProvider):
    slug = models.SlugField(
        _('unique text id'),
        max_length=50,
        unique=True)

    start_url = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )

    allowed_ips = models.CharField(
        _('allowed ips'),
        help_text=_('A comma separated list of allowed ips. Leave blank to disable ip restriction.'),
        max_length=255,
        null=True,
        blank=True,
    )

    allow_access_by_email_suffix = models.CharField(
        _('allow access by email'),
        null=True,
        blank=True,
        max_length=255,
        help_text=_(
            ('A comma separated list of email domains, e.g. "mobile.ukti.gov.uk, trade.gsi.gov.uk, fco.gov.uk" '
             'User\'s with an email in this list will be given access.  NOTE: all user emails are checked - '
             'including aliases.')
        )
    )

    objects = models.Manager()

    ### The following properties exist so that this model has the same fields as
    ### `oauth2.Application`

    @property
    def application_key(self):
        return self.slug

    @property
    def name(self):
        return self.pretty_name

    @property
    def display_name(self):
        return self.pretty_name

    def is_valid_ip(self, request):
        if not self.allowed_ips or not self.allowed_ips.strip():
            return True

        client_ip = get_client_ip(request)

        if not client_ip:
            return False

        return client_ip in self.allowed_ips
