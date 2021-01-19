import logging

from django.db import models
<<<<<<< HEAD
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
=======
from django.utils.translation import gettext_lazy as _
>>>>>>> Django 3 upgrade preliminaries

from sso.core.ip_filter import get_client_ip

logger = logging.getLogger(__file__)

### Temporary upgrade model

DEFAULT_ATTRIBUTE_MAPPING = {
    # DJANGO: SAML
    'email': 'email',
    'first_name': 'first_name',
    'last_name': 'last_name',
    'is_staff': 'is_staff',
    'is_superuser': 'is_superuser',
}

DEFAULT_PROCESSOR = 'sso.samlidp.processors.ModelProcessor'


def get_default_processor() -> str:
    if hasattr(settings, 'SAML_IDP_SP_FIELD_DEFAULT_PROCESSOR'):
        return getattr(settings, 'SAML_IDP_SP_FIELD_DEFAULT_PROCESSOR')
    return DEFAULT_PROCESSOR


def get_default_attribute_mapping() -> str:
    if hasattr(settings, 'SAML_IDP_SP_FIELD_DEFAULT_ATTRIBUTE_MAPPING'):
        return json.dumps(getattr(settings, 'SAML_IDP_SP_FIELD_DEFAULT_ATTRIBUTE_MAPPING'))
    return json.dumps(DEFAULT_ATTRIBUTE_MAPPING)


class SamlApplication(models.Model):
    slug = models.SlugField(
        _('slug'),
        help_text=_('WARNING: changing this may break things.')
    )

    dt_created = models.DateTimeField(verbose_name='Created at', auto_now_add=True)
    dt_updated = models.DateTimeField(verbose_name='Updated at', auto_now=True, null=True, blank=True)

    pretty_name = models.CharField(verbose_name='Pretty Name', blank=True, max_length=255, help_text='For display purposes, can be empty')
    description = models.TextField(verbose_name='Description', blank=True)
    metadata_expiration_dt = models.DateTimeField(verbose_name='Metadata valid until')
    local_metadata = models.TextField(verbose_name='Local Metadata XML', blank=True, help_text='XML containing the metadata')
    active = models.BooleanField(verbose_name='Active', default=True)
    _processor = models.CharField(verbose_name='Processor', max_length=256, help_text='Import string for the (access) Processor to use.', default='get_default_processor')
    _attribute_mapping = models.TextField(verbose_name='Attribute mapping', default='get_default_attribute_mapping', help_text='dict with the mapping from django attributes to saml attributes in the identity.')
    _nameid_field = models.CharField(verbose_name='NameID Field', blank=True, max_length=64, help_text='Attribute on the user to use as identifier during the NameID construction. Can be a callable. If not set, this will default to settings.SAML_IDP_DJANGO_USERNAME_FIELD; if that is not set, it will use the `USERNAME_FIELD` attribute on the active user model.')

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

    @property
    def public(self):
        return False

    @property
    def display_name(self):
        return self.name

    @property
    def application_key(self):
        return self.entity_id

    def __str__(self):
        return self.name

    def is_valid_ip(self, request):
        if not self.allowed_ips or not self.allowed_ips.strip():
            return True

        client_ip = get_client_ip(request)

        if not client_ip:
            return False

        return client_ip in self.allowed_ips
