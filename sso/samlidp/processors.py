from djangosaml2idp.processors import BaseProcessor

from .models import SamlApplication


class ModelProcessor(BaseProcessor):
    """
    Load an associated `sso.samlidp.models.SamlApplication` model
    """

    def __init__(self, entity_id, *args, **kwargs):
        self._application = SamlApplication.objects.get(entity_id=entity_id)

    def has_access(self, user):
        return user.can_access(self._application)


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
