import logging
import ipaddress
import re

from ipware.ip import get_real_ip
from django.conf import settings


log = logging.getLogger(__name__)


def is_trusted_ip(request, trusted_ips=None):
    """Check that `source_ip` is in a valid range"""

    if not trusted_ips:
        trusted_ips = [ip.strip() for ip in settings.TRUSTED_IPS.split(',')]

    # get_real_ip requires a django Request object, but we're provided with a oauthlib.Request object.
    # So we're exposing the headers key as request.META to allow get_real_ip to work
    class DjangoRequest:
        def __init__(self, request_headers):
            self.META = request_headers

    client_ip = get_real_ip(DjangoRequest(request.headers))

    if not client_ip:
        log.warn('Cannot determine client IP address')
        return False

    return ip_in_range(client_ip, trusted_ips=trusted_ips)


def ip_in_range(client_ip, trusted_ips):
    for ip in trusted_ips:
        if is_cidr(ip) and ipaddress.ip_address(client_ip) in ipaddress.ip_network(ip):
            return True
        elif client_ip == ip:
            return True

    return False


def is_cidr(ip):
    CIDR_REGEX = '^([0-9]{1,3}\.){3}[0-9]{1,3}(\/\d+){1}$'

    return re.match(CIDR_REGEX, ip) is not None
