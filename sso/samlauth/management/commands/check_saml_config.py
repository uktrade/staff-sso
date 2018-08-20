from django.core.management.base import BaseCommand

"""
Attempt to load the SAML config and output any exceptions that occur.

This is a bit of a blunt instrument, but provides a check CI can use.

Useful references:
  pysaml2/conf.py 
"""

import copy
import sys

from django.conf import settings
from djangosaml2.conf import SPConfig


def _get_saml_config(disable_key_checks=False):
    saml_config = copy.deepcopy(settings.SAML_CONFIG)
    if disable_key_checks:
        del saml_config['key_file']
        del saml_config['cert_file']
    return saml_config


def _load_saml_config(disable_key_checks=False):
    """
    Attempt to load config, pysaml2 will raise exceptions if there are issues.

    :param disable_key_checks: disable checking for key and certificate files

    Disabling the checks the check key checks is useful if you need to check
    the rest of the configuration, but the keys are not available.
    """
    saml_config = _get_saml_config(disable_key_checks)

    conf = SPConfig()
    conf.disable_ssl_certificate_validation = disable_key_checks
    conf.load(saml_config)  # raises exceptions on incorrect config


def display_idp_config_issues(disable_key_checks=False):
    """
    Attempt to load config, display any errors to the console.

    :param disable_key_checks: disable checking for key and certificate files
    :return True if idp loaded successfully
    """
    try:
        _load_saml_config(disable_key_checks)
        return True
    except Exception as e:
        print(e, file=sys.stderr)
        return False


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--disable_key_checks',
                            action='store_true',
                            default=False,
                            help='Do not attempt to load key files')

    def handle(self, *args, **options):
        disable_key_checks = options['disable_key_checks']
        result = display_idp_config_issues(disable_key_checks)
        if not result:
            sys.exit(1)
