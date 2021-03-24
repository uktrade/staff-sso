import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from djangosaml2idp.models import AbstractServiceProvider

from sso.core.ip_filter import get_client_ip

logger = logging.getLogger(__file__)


class SamlApplication(AbstractServiceProvider):
    slug = models.SlugField(_("unique text id"), max_length=50, unique=True)

    real_entity_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_(
            "Takes precendence over the entity_id field and allows for the entity_id field to be an alias"
        ),
    )

    start_url = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )

    allowed_ips = models.CharField(
        _("allowed ips"),
        help_text=_(
            "A comma separated list of allowed ips. Leave blank to disable ip restriction."
        ),
        max_length=255,
        null=True,
        blank=True,
    )

    allow_access_by_email_suffix = models.CharField(
        _("allow access by email"),
        null=True,
        blank=True,
        max_length=255,
        help_text=_(
            (
                'A comma separated list of email domains, e.g. "mobile.ukti.gov.uk, trade.gsi.gov.uk, fco.gov.uk" '
                "User's with an email in this list will be given access.  NOTE: all user emails are checked - "
                "including aliases."
            )
        ),
    )

    extra_config = models.JSONField(
        _("extra configuration"),
        help_text=_("Additional configuration used by custom processors."),
        blank=True,
        default=dict,
    )

    objects = models.Manager()

    ### The following properties exist so that this model has the same fields as
    ### `oauth2.Application`

    @property
    def application_key(self):
        return self.slug

    @property
    def display_name(self):
        return self.pretty_name

    @property
    def name(self):
        return self.pretty_name

    @property
    def public(self):
        return False

    def is_valid_ip(self, request):
        if not self.allowed_ips or not self.allowed_ips.strip():
            return True

        client_ip = get_client_ip(request)

        if not client_ip:
            return False

        return client_ip in self.allowed_ips

    def get_entity_id(self):
        return self.real_entity_id or self.entity_id
