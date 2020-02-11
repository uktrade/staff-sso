import logging

from django.conf import settings

from djangosaml2idp.processors import BaseProcessor


from .models import SamlApplication
from sso.user.models import EmailAddress
from sso.core.logging import create_x_access_log


logger = logging.getLogger(__name__)


def build_google_user_id(user):
    """
    Construct a google email address from the user's primary email.
    """

    try:
        return user.emails.get(email__endswith='@'+settings.MI_GOOGLE_EMAIL_DOMAIN).email
    except EmailAddress.DoesNotExist:
        return '{}@{}'.format(
            user.email.split('@')[0],
            settings.MI_GOOGLE_EMAIL_DOMAIN)


class ModelProcessor(BaseProcessor):
    """
    Load an associated `sso.samlidp.models.SamlApplication` model
    """

    def __init__(self, entity_id, *args, **kwargs):
        self._application = SamlApplication.objects.get(entity_id=entity_id)

    def has_access(self, request):

        access = request.user.can_access(self._application) and \
                 self._application.enabled and self._application.is_valid_ip(request)

        create_x_access_log(
            request,
            200 if access else 403,
            application=self._application.name
        )

        return access


class AWSProcessor(ModelProcessor):
    def create_identity(self, user, sp_mapping, **extra_config):

        role_arn = extra_config.pop('role', None)

        assert role_arn, 'missing AWS role arn'

        # See: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml_assertions.html
        # The role and saml arns should be added to `settings.SAML_IDP_SPCONFIG['{saml2-entity-id}']['role']

        identity = super().create_identity(user, sp_mapping)

        identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] = str(user.user_id)
        identity['https://aws.amazon.com/SAML/Attributes/Role'] = role_arn

        return identity


class GoogleProcessor(ModelProcessor):
    def get_user_id(self, user):
        return build_google_user_id(user)


class InvisionProcessor(ModelProcessor):
    def get_user_id(self, user):
        return user.email


class EmailIdProcessor(ModelProcessor):
    def get_user_id(self, user):
        return user.email_user_id
