import urllib.parse
import time

import mohawk
from django.urls import reverse
import pytest

from .factories.user import UserFactory


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


@pytest.mark.django_db
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


@pytest.mark.django_db
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


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_if_no_users_no_activities_one_page(api_client):
    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')
    response = hawk_request(api_client, host, path)
    response_dict = response.json()
    assert response_dict['orderedItems'] == []
    assert 'next' not in response_dict


@pytest.mark.django_db
def test_if_one_user_one_activity_two_pages_then_updates(api_client):
    UserFactory()

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict['orderedItems']) == 1
    assert 'next' in response_1_dict

    next_str = response_1_dict['next']
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_2_dict = response_2.json()
    assert response_2_dict['orderedItems'] == []
    assert 'next' not in response_2_dict

    UserFactory()

    response_3 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_3_dict = response_3.json()
    assert len(response_3_dict['orderedItems']) == 1
    assert 'next' in response_3_dict

    next_str = response_3_dict['next']
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_4 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_4_dict = response_4.json()
    assert response_4_dict['orderedItems'] == []
    assert 'next' not in response_4_dict


@pytest.mark.django_db
def test_if_50_users_two_pages(api_client):
    UserFactory.create_batch(50)

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    response_1_dict = response_1.json()

    assert len(response_1_dict['orderedItems']) == 50
    assert 'next' in response_1_dict

    next_str = response_1_dict['next']
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_2_dict = response_2.json()
    assert response_2_dict['orderedItems'] == []
    assert 'next' not in response_2_dict


@pytest.mark.django_db
def test_if_51_users_three_pages(api_client):
    UserFactory.create_batch(51)

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    response_1_dict = response_1.json()
    assert len(response_1_dict['orderedItems']) == 50
    assert 'next' in response_1_dict

    next_str = response_1_dict['next']
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_2_dict = response_2.json()
    assert len(response_2_dict['orderedItems']) == 1
    assert 'next' in response_2_dict

    next_str = response_2_dict['next']
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_3 = hawk_request(api_client, host, next_url.path + (f'?{next_url.query}' if next_url.query else ''))
    response_3_dict = response_3.json()
    assert response_3_dict['orderedItems'] == []
    assert 'next' not in response_3_dict


@pytest.mark.django_db
def test_no_n_plus_1_query(api_client, django_assert_num_queries):
    UserFactory.create_batch(50)

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    with django_assert_num_queries(2):
        response_1 = hawk_request(api_client, host, path)


@pytest.mark.django_db
def test_with_contact_email(api_client):
    UserFactory(email='test@a.com', contact_email='test@b.com', email_list=['test@c.com', 'test@d.com'])

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict['orderedItems']) == 1
    assert response_1_dict['orderedItems'][0]['object']['dit:emailAddress'] == [
        'test@b.com', 'test@a.com', 'test@c.com', 'test@d.com',
    ]


@pytest.mark.django_db
def test_without_contact_email(api_client):
    UserFactory(email='test@a.com', email_list=['test@b.com', 'test@c.com'])

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict['orderedItems']) == 1
    assert response_1_dict['orderedItems'][0]['object']['dit:emailAddress'] == [
        'test@a.com', 'test@b.com', 'test@c.com',
    ]


def hawk_auth_header(key_id, secret_key, url, method, content, content_type):
    return mohawk.Sender({
        'id': key_id,
        'key': secret_key,
        'algorithm': 'sha256',
    }, url, method, content=content, content_type=content_type).request_header


def hawk_request(api_client, host, path):
    url = f'http://{host}{path}'
    return api_client.get(path,
        content_type=None,
        HTTP_HOST='localhost:8080',
        HTTP_AUTHORIZATION=hawk_auth_header('the-id', 'the-secret', url, 'GET', b'', ''),
    )
