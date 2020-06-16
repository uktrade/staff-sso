import mohawk
from django.urls import reverse
import pytest


def test_via_public_internet_then_403(api_client):
    path = reverse('api-v1:core:activity-stream')
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type=None,
        HTTP_X_FORWARDED_FOR='',
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header('the-id', 'the-secret', url, 'GET', b'', ''),
    )
    assert response.status_code == 403
    assert response.json() == {}


def test_no_auth_header_then_403(api_client):
    path = reverse('api-v1:core:activity-stream')
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type=None,
        HTTP_HOST='localhost:8080',
    )
    assert response.status_code == 403
    assert response.json() == {}


@pytest.mark.parametrize('get_hawk_params', [
    (lambda url: ('not-the-id', 'the-secret', url, 'GET', b'', '')),
    (lambda url: ('the-id', 'not-the-secret', url, 'GET', b'', '')),
    (lambda url: ('the-id', 'the-secret', url + 'not', 'GET', b'', '')),
    (lambda url: ('the-id', 'the-secret', url, 'POST', b'', '')),
    (lambda url: ('the-id', 'the-secret', url, 'GET', b'not', '')),
    (lambda url: ('the-id', 'the-secret', url, 'GET', b'', 'not')),
])
def test_bad_auth_header_then_403(api_client, get_hawk_params):
    path = reverse('api-v1:core:activity-stream')
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type=None,
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header(*get_hawk_params(url)),
    )
    assert response.status_code == 403
    assert response.json() == {}


def test_via_internal_networking_with_content_type_then_200(api_client):
    # The Activity Stream does not send a content-type header. However, we
    # shouldn't be brittle WRT that
    path = reverse('api-v1:core:activity-stream')
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type='text/plain',
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header('the-id', 'the-secret', url, 'GET', b'', 'text/plain'),
    )
    assert response.status_code == 200


def test_via_internal_networking_with_query_string_then_200(api_client):
    path = reverse('api-v1:core:activity-stream') + '?some=param&another=param'
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type=None,
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header('the-id', 'the-secret', url, 'GET', b'', ''),
    )
    assert response.status_code == 200


def test_via_internal_networking_no_content_type_then_200(api_client):
    path = reverse('api-v1:core:activity-stream')
    host = 'localhost:8080'
    url = f'http://{host}{path}'
    response = api_client.get(path,
        content_type=None,
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header('the-id', 'the-secret', url, 'GET', b'', ''),
    )
    assert response.status_code == 200


def hawk_auth_header(key_id, secret_key, url, method, content, content_type):
    return mohawk.Sender({
        'id': key_id,
        'key': secret_key,
        'algorithm': 'sha256',
    }, url, method, content=content, content_type=content_type).request_header
