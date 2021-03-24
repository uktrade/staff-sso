import logging
from typing import Any, Optional, Tuple

from django.conf import settings
from djangosaml2.backends import Saml2Backend

try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError:

    class SiteProfileNotAvailable(Exception):
        pass


logger = logging.getLogger("djangosaml2")


class MultiEmailSaml2Backend(Saml2Backend):
    def get_or_create_user(
        self,
        user_lookup_key: str,
        user_lookup_value: Any,
        create_unknown_user: bool,
        idp_entityid: str,
        attributes: dict,
        attribute_mapping: dict,
        request,
    ) -> Tuple[Optional[settings.AUTH_USER_MODEL], bool]:

        params = {user_lookup_key: user_lookup_value}

        UserModel = self._user_model

        try:
            user, created = UserModel.objects.get_by_email(user_lookup_value), False
        except UserModel.DoesNotExist:
            user, created = UserModel.objects.create(**params), True

        return user, created

    def is_user_authorized(self, user) -> bool:
        """ Hook to allow for additional authorization based on user settings, e.g is_active """
        return user and user.is_active
