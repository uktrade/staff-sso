from djangosaml2.backends import Saml2Backend as DjangoSaml2Backend


class Saml2Backend(DjangoSaml2Backend):
    def authenticate(self, **kwargs):
        """
        Extends the default djangosaml2 Saml2Backend checking if the
        user can authenticate as well (e.g. .is_active == True).
        """
        user = super().authenticate(**kwargs)
        if user and self.user_can_authenticate(user):
            return user
