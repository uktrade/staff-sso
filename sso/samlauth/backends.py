import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from djangosaml2.backends import Saml2Backend

from djangosaml2.signals import pre_user_save

try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError:
    class SiteProfileNotAvailable(Exception):
        pass


logger = logging.getLogger('djangosaml2')


class MultiEmailSaml2Backend(Saml2Backend):

    def authenticate(self, session_info=None, attribute_mapping=None,
                     create_unknown_user=True, **kwargs):

        if session_info is None or attribute_mapping is None:
            logger.error('Session info or attribute mapping are None')
            return None

        if not 'ava' in session_info:
            logger.error('"ava" key not found in session_info')
            return None

        attributes = session_info['ava']
        if not attributes:
            logger.error('The attributes dictionary is empty')

        use_name_id_as_username = getattr(
            settings, 'SAML_USE_NAME_ID_AS_USERNAME', False)

        django_user_main_attribute = settings.SAML_DJANGO_USER_MAIN_ATTRIBUTE
        django_user_main_attribute_lookup = settings.SAML_DJANGO_USER_MAIN_ATTRIBUTE_LOOKUP

        # Selectively use the nameid field for IdPs in this list.
        ids_use_name_id_as_username = getattr(
            settings, 'SAML_IDPS_USE_NAME_ID_AS_USERNAME', [])

        logger.debug('attributes: %s', attributes)
        saml_user = None

        if use_name_id_as_username or session_info['issuer'] in ids_use_name_id_as_username:
            if 'name_id' in session_info:
                logger.debug('name_id: %s', session_info['name_id'])
                saml_user = session_info['name_id'].text
            else:
                logger.error('The nameid is not available. Cannot find user without a nameid.')
        else:
            saml_user = self.get_attribute_value(django_user_main_attribute, attributes, attribute_mapping)

        if saml_user is None:
            logger.error('Could not find saml_user value')
            return None

        if not self.is_authorized(attributes, attribute_mapping):
            return None

        main_attribute = self.clean_user_main_attribute(saml_user)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.

        return self.get_saml2_user(
            create_unknown_user, main_attribute, attributes, attribute_mapping)

    def update_user(self, user, attributes, attribute_mapping,
                    force_save=False):
        """Update a user with a set of attributes and returns the updated user.

        By default it uses a mapping defined in the settings constant
        SAML_ATTRIBUTE_MAPPING. For each attribute, if the user object has
        that field defined it will be set, otherwise it will try to set
        it in the profile object.
        """

        if not attribute_mapping:
            return user

        try:
            profile = user.get_profile()
        except ObjectDoesNotExist:
            profile = None
        except SiteProfileNotAvailable:
            profile = None
        # Django 1.5 custom model assumed
        except AttributeError:
            profile = user

        user_modified = False
        profile_modified = False

        for saml_attr, django_attrs in attribute_mapping.items():
            try:
                for attr in django_attrs:
                    # do not overwrite the main attribute, e.g. email field,
                    # which is set on creation and does not need to be updated.
                    if attr == settings.SAML_DJANGO_USER_MAIN_ATTRIBUTE:
                        continue

                    if hasattr(user, attr):
                        user_attr = getattr(user, attr)
                        if callable(user_attr):
                            modified = user_attr(
                                attributes[saml_attr])
                        else:
                            modified = self._set_attribute(
                                user, attr, attributes[saml_attr][0])

                        user_modified = user_modified or modified

                    elif profile is not None and hasattr(profile, attr):
                        modified = self._set_attribute(
                            profile, attr, attributes[saml_attr][0])
                        profile_modified = profile_modified or modified

            except KeyError:
                # the saml attribute is missing
                pass

        logger.debug('Sending the pre_save signal')
        signal_modified = any(
            [response for receiver, response
             in pre_user_save.send_robust(sender=user.__class__,
                                          instance=user,
                                          attributes=attributes,
                                          user_modified=user_modified)]
        )

        if user_modified or signal_modified or force_save:
            user.save()

        if (profile is not None
            and (profile_modified or signal_modified or force_save)):
            profile.save()

        return user
