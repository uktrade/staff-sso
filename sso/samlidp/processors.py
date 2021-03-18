import logging

from django.conf import settings

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

    def get_user_id(self, user):
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

    def create_identity(self, user, sp_mapping, **extra_config):

        role_arn = extra_config.pop('role', None)

        assert role_arn, 'missing AWS role arn'

        # See: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml_assertions.html
        # The role and saml arns should be added to `settings.SAML_IDP_SPCONFIG['{saml2-entity-id}']['role']

        identity = super().create_identity(user, sp_mapping)

        identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] = self.get_user_id(user)
        identity['https://aws.amazon.com/SAML/Attributes/Role'] = role_arn

        return identity
