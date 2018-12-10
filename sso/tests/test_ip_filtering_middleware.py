from django.http import HttpResponse

from sso.core.ip_filter import get_client_ip
from sso.core.middleware import AdminIpRestrictionMiddleware


def test_get_client_ip_no_header(rf):
    request = rf.get('/whatever/')

    client_ip = get_client_ip(request)

    assert client_ip is None


def test_get_client_ip(rf):
    request = rf.get('/whatever/', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')

    client_ip = get_client_ip(request)

    assert client_ip == '1.1.1.1'


def test_ip_restriction_middleware_is_enabled(client, settings):
    settings.RESTRICT_ADMIN = True
    assert client.get('/admin/').status_code == 401


def test_ip_restriction_applies_to_admin_only(rf, settings):
    settings.RESTRICT_ADMIN = True

    request = rf.get('/access-denied/')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 200  # noqa


def test_ip_restriction_enabled_false(rf, settings):
    settings.RESTRICT_ADMIN = False

    request = rf.get('/admin/', HTTP_X_FORWARDED_FOR='')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 200  # noqa


def test_ip_restriction_missing_x_forwarded_header(rf, settings):
    settings.RESTRICT_ADMIN = True

    request = rf.get('/admin/', HTTP_X_FORWARDED_FOR='1.1.1.1')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 401  # noqa


def test_ip_restriction_invalid_x_forwarded_header(rf, settings):
    settings.RESTRICT_ADMIN = True

    request = rf.get('/admin/', HTTP_X_FORWARDED_FOR='1.1.1.1')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 401  # noqa


def test_ip_restriction_valid_ip(rf, settings):
    settings.RESTRICT_ADMIN = True
    settings.ALLOWED_ADMIN_IPS = ['1.1.1.1']

    request = rf.get('/admin/',
                     HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 200  # noqa


def test_ip_restriction_invalid_ip(rf, settings):
    settings.RESTRICT_ADMIN = True
    settings.ALLOWED_ADMIN_IPS = ['2.2.2.2']

    request = rf.get('/admin/',
                     HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 401  # noqa

    settings.ALLOWED_ADMIN_IPS = ['3.3.3.3']

    assert AdminIpRestrictionMiddleware(lambda _: HttpResponse(status=200))(request).status_code == 401  # noqa
