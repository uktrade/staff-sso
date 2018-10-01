from djangosaml2idp.processors import BaseProcessor


class AWSProcessor(BaseProcessor):
    def create_identity(self, user, sp_mapping):

        identity = super().create_identity(user, sp_mapping)

        identity['https://aws.amazon.com/SAML/Attributes/Role'] = 'arn:aws:iam::165562107270:role/quicksight_federation,arn:aws:iam::165562107270:saml-provider/staff_sso_uat'
        identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] = user.email

        return identity
