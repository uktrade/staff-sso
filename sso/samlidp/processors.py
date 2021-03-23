import logging
from typing import Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djangosaml2idp.processors import BaseProcessor


from .models import SamlApplication
from sso.user.models import EmailAddress, ServiceEmailAddress
from sso.core.logging import create_x_access_log


logger = logging.getLogger(__name__)


class ModelProcessor(BaseProcessor):
    """
    Load an associated `sso.samlidp.models.SamlApplication` model
    """

    USER_ID_FIELD = 'email'

    def __init__(self, entity_id, *args, **kwargs):
        self._application = SamlApplication.objects.get(entity_id=entity_id)

    def get_user_id(self, user, name_id_format: str, service_provider: SamlApplication, idp_config):
        return str(self.get_service_email(user) or getattr(user, self.USER_ID_FIELD) or user.email)

    def get_service_email(self, user):
        """Get the email address specified for this user & service.

        Returns None if a service email isn't defined """
        try:
            return user.service_emails.get(saml_application=self._application).email.email
        except ServiceEmailAddress.DoesNotExist:
            return None

    def has_access(self, request):

        access = request.user.can_access(self._application) and \
                 self._application.active and self._application.is_valid_ip(request)

        create_x_access_log(
            request,
            200 if access else 403,
            application=self._application.pretty_name
        )

        return access


class AWSProcessor(ModelProcessor):
    USER_ID_FIELD = 'user_id'

    def create_identity(self, user, sp_attribute_mapping: Dict[str, str]) -> Dict[str, str]:

        # See: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml_assertions.html
        # The role and saml arns should be added to the extra_config field of the saml application

        identity = super().create_identity(user, sp_attribute_mapping)

        try:
            role = self._application.extra_config['role']
        except KeyError:
            raise ImproperlyConfigured('AWS processor requires a role to be provided in extra_config')

        identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] = self.get_user_id(user, None, None, None)
        identity['https://aws.amazon.com/SAML/Attributes/Role'] = role

        return identity


class ApplicationPermissionProcessor(ModelProcessor):
    """Include application permissions as a list of groups"""
    
    def create_identity(self, user, sp_mapping, **extra_config):

        identity = super().create_identity(user, sp_mapping)

        permissions = list(
            user.application_permissions
                .filter(saml2_application=self._application)
                .values_list('permission', flat=True))

        identity['groups'] = permissions

        return identity
