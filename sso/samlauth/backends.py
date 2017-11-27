import logging

from django.core.exceptions import MultipleObjectsReturned
from djangosaml2 import settings as saml_settings
from djangosaml2.backends import get_saml_user_model, Saml2Backend

try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError:
    class SiteProfileNotAvailable(Exception):
        pass


logger = logging.getLogger('djangosaml2')


class MultiEmailSaml2Backend(Saml2Backend):

    def _get_saml2_user(self, main_attribute, attributes, attribute_mapping):
        # TODO: make this use email aliases, e.g. the user.emails list.
        User = get_saml_user_model()
        django_user_main_attribute = saml_settings.SAML_DJANGO_USER_MAIN_ATTRIBUTE
        user_query_args = self.get_user_query_args(main_attribute)

        logger.debug('Retrieving existing user "%s"', main_attribute)
        try:
            user = User.objects.get(**user_query_args)
            user = self.update_user(user, attributes, attribute_mapping)
        except User.DoesNotExist:
            logger.error('The user "%s" does not exist', main_attribute)
            return None
        except MultipleObjectsReturned:
            logger.error('There are more than one user with %s = %s',
                         django_user_main_attribute, main_attribute)
            return None
        return user
