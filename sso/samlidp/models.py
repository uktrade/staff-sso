from django.db import models
from django.utils.translation import ugettext_lazy as _


class SamlApplication(models.Model):
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
    ip_restriction = models.CharField(
        _('ip restriction'),
        help_text=_('A comma separated list of allowed ips. Leave blank to disable ip restriction.'),
        max_length=255,
        null=True,
        blank=True,
    )
    enabled = models.BooleanField(
        _('Enabled?'),
        default=True,
        help_text=_('Is this integration enabled?'),
    )

    def __str__(self):
        return self.name
