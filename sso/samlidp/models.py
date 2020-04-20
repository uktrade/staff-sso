import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from sso.core.ip_filter import get_client_ip

logger = logging.getLogger(__file__)


class SamlApplication(models.Model):
    slug = models.SlugField(
        _('slug'),
        help_text=_('WARNING: changing this may break things.')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
    )
    start_url = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    entity_id = models.CharField(
        _('Saml2 entity id'),
        max_length=255,
        unique=True,
        help_text=_('The entity ID of the service provider. WARNING: changing this may break the integration.'),
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
    enabled = models.BooleanField(
        _('Enabled?'),
        default=True,
        help_text=_('Is this integration enabled?'),
    )

    def __str__(self):
        return self.name

    def is_valid_ip(self, request):
        if not self.allowed_ips or not self.allowed_ips.strip():
            return True

        client_ip = get_client_ip(request)

        if not client_ip:
            return False

        return client_ip in self.allowed_ips
