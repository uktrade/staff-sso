import time
import urllib.parse

import mohawk
import pytest
from django.urls import reverse
from freezegun import freeze_time

from sso.user.middleware import UpdatedLastAccessedMiddleware
from .factories.oauth import ApplicationFactory
from .factories.saml import SamlApplicationFactory
from .factories.user import AccessProfileFactory, UserFactory


def test_via_public_internet_then_403(api_client):
    path = reverse("api-v1:core:activity-stream")
    host = "localhost:8080"
    url = f"http://{host}{path}"
    response = api_client.get(
        path,
        content_type=None,
        HTTP_X_FORWARDED_FOR="",
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header("the-id", "the-secret", url, "GET", b"", ""),
    )
    assert response.status_code == 403
    assert response.json() == {}


def test_no_auth_header_then_403(api_client):
    path = reverse("api-v1:core:activity-stream")

    response = api_client.get(
        path,
        content_type=None,
        HTTP_HOST="localhost:8080",
    )
    assert response.status_code == 403
    assert response.json() == {}


@pytest.mark.parametrize(
    "get_hawk_params",
    [
        (lambda url: ("not-the-id", "the-secret", url, "GET", b"", "")),
        (lambda url: ("the-id", "not-the-secret", url, "GET", b"", "")),
        (lambda url: ("the-id", "the-secret", url + "not", "GET", b"", "")),
        (lambda url: ("the-id", "the-secret", url, "POST", b"", "")),
        (lambda url: ("the-id", "the-secret", url, "GET", b"not", "")),
        (lambda url: ("the-id", "the-secret", url, "GET", b"", "not")),
    ],
)
def test_bad_auth_header_then_403(api_client, get_hawk_params):
    path = reverse("api-v1:core:activity-stream")
    host = "localhost:8080"
    url = f"http://{host}{path}"
    response = api_client.get(
        path,
        content_type=None,
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header(*get_hawk_params(url)),
    )
    assert response.status_code == 403
    assert response.json() == {}


@pytest.mark.django_db
def test_via_internal_networking_with_content_type_then_200(api_client):
    # The Activity Stream does not send a content-type header. However, we
    # shouldn't be brittle WRT that
    path = reverse("api-v1:core:activity-stream")
    host = "localhost:8080"
    url = f"http://{host}{path}"
    response = api_client.get(
        path,
        content_type="text/plain",
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header("the-id", "the-secret", url, "GET", b"", "text/plain"),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_via_internal_networking_with_query_string_then_200(api_client):
    path = reverse("api-v1:core:activity-stream") + "?some=param&another=param"
    host = "localhost:8080"
    url = f"http://{host}{path}"
    response = api_client.get(
        path,
        content_type=None,
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header("the-id", "the-secret", url, "GET", b"", ""),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_via_internal_networking_no_content_type_then_200(api_client):
    path = reverse("api-v1:core:activity-stream")
    host = "localhost:8080"
    url = f"http://{host}{path}"
    response = api_client.get(
        path,
        content_type=None,
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header("the-id", "the-secret", url, "GET", b"", ""),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_if_no_users_no_activities_one_page(api_client):
    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")
    response = hawk_request(api_client, host, path)
    response_dict = response.json()
    assert response_dict["orderedItems"] == []
    assert "next" not in response_dict


@pytest.mark.django_db
def test_if_one_user_one_activity_two_pages_then_updates(api_client):
    UserFactory()
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 1
    assert "next" in response_1_dict

    next_str = response_1_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_2_dict = response_2.json()
    assert response_2_dict["orderedItems"] == []
    assert "next" not in response_2_dict

    UserFactory()
    time.sleep(1)

    response_3 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_3_dict = response_3.json()
    assert len(response_3_dict["orderedItems"]) == 1
    assert "next" in response_3_dict

    next_str = response_3_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_4 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_4_dict = response_4.json()
    assert response_4_dict["orderedItems"] == []
    assert "next" not in response_4_dict


@pytest.mark.django_db
def test_if_50_users_two_pages(api_client):
    UserFactory.create_batch(50)
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 50
    assert "next" in response_1_dict

    next_str = response_1_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_2_dict = response_2.json()
    assert response_2_dict["orderedItems"] == []
    assert "next" not in response_2_dict


@pytest.mark.django_db
def test_if_51_users_three_pages(api_client):
    UserFactory.create_batch(51)
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    response_1_dict = response_1.json()
    assert len(response_1_dict["orderedItems"]) == 50
    assert "next" in response_1_dict

    next_str = response_1_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_2_dict = response_2.json()
    assert len(response_2_dict["orderedItems"]) == 1
    assert "next" in response_2_dict

    next_str = response_2_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_3 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_3_dict = response_3.json()
    assert response_3_dict["orderedItems"] == []
    assert "next" not in response_3_dict


@pytest.mark.django_db
def test_no_n_plus_1_query(api_client, django_assert_num_queries):
    ap = AccessProfileFactory()
    ap.oauth2_applications.add(ApplicationFactory())
    ap.saml2_applications.add(SamlApplicationFactory())
    app_direct = ApplicationFactory()
    UserFactory.create_batch(50, add_access_profiles=[ap], add_permitted_applications=[app_direct])

    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    with django_assert_num_queries(7):
        hawk_request(api_client, host, path)


@pytest.mark.django_db
def test_with_permitted_apps(api_client, django_assert_num_queries):
    ap = AccessProfileFactory()
    ap.oauth2_applications.add(ApplicationFactory(display_name="App C", start_url="https://c.com/"))
    ap.saml2_applications.add(
        SamlApplicationFactory(pretty_name="App B", start_url="https://b.com/")
    )
    app_direct = ApplicationFactory(display_name="App A", start_url="https://a.com/")
    app_no_access = ApplicationFactory(  # noqa: F841
        display_name="App D", start_url="https://d.com/"
    )
    UserFactory(add_access_profiles=[ap], add_permitted_applications=[app_direct])

    ApplicationFactory(
        display_name="App E", start_url="https://e.com/", default_access_allowed=True
    )

    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response = hawk_request(api_client, host, path)
    response_dict = response.json()

    assert len(response_dict["orderedItems"]) == 1

    assert response_dict["orderedItems"][0]["object"][
        "dit:StaffSSO:User:permittedApplications"
    ] == [
        {
            "name": "App A",
            "url": "https://a.com/",
        },
        {
            "name": "App B",
            "url": "https://b.com/",
        },
        {
            "name": "App C",
            "url": "https://c.com/",
        },
        {
            "name": "App E",
            "url": "https://e.com/",
        },
    ]


@pytest.mark.django_db
def test_with_contact_email(api_client):
    UserFactory(
        email="test@a.com", contact_email="test@b.com", email_list=["test@c.com", "test@d.com"]
    )
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 1
    assert response_1_dict["orderedItems"][0]["object"]["dit:emailAddress"] == [
        "test@a.com",
        "test@c.com",
        "test@d.com",
    ]


@pytest.mark.django_db
def test_without_contact_email(api_client):
    UserFactory(email="test@a.com", email_list=["test@b.com", "test@c.com"])
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 1
    assert response_1_dict["orderedItems"][0]["object"]["dit:emailAddress"] == [
        "test@a.com",
        "test@b.com",
        "test@c.com",
    ]


@pytest.mark.django_db
def test_active_and_inactive(api_client):
    UserFactory(is_active=True)
    UserFactory(is_active=False)
    time.sleep(1)

    host = 'localhost:8080'
    path = reverse('api-v1:core:activity-stream')

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict['orderedItems']) == 2
    response_1_dict['orderedItems'][0]['object']['dit:StaffSSO:User:status'] == 'active'
    response_1_dict['orderedItems'][1]['object']['dit:StaffSSO:User:status'] == 'inactive'

@pytest.mark.django_db
def test_last_accessed_in_full_ingest(api_client, rf, mocker):
    user = UserFactory(email="test@a.com", email_list=["test@b.com", "test@c.com"])
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 1
    assert response_1_dict["orderedItems"][0]["object"]["dit:StaffSSO:User:lastAccessed"] is None

    middleware = UpdatedLastAccessedMiddleware(get_response=mocker.MagicMock())
    request = rf.get("/")
    request.user = user
    with freeze_time("1995-01-16 15:50:00"):
        middleware(request)

    response_2 = hawk_request(api_client, host, path)
    assert response_2.status_code == 200
    response_2_dict = response_2.json()

    assert len(response_2_dict["orderedItems"]) == 1
    assert (
        response_2_dict["orderedItems"][0]["object"]["dit:StaffSSO:User:lastAccessed"]
        == "1995-01-16T15:50:00Z"
    )


@pytest.mark.django_db
def test_user_access_does_not_result_in_update(api_client, rf, mocker):
    # If a client wants to have the last login for a user, they have to wait for the next full
    # ingest from the Activity Stream: we do this to not pollute real-time updates which at the
    # time of writing are only used for email addresses. If we need real-time update of last access
    # we would probably want another type of activity, with two interplexed streams of activities.
    # Note also at the time of writing, a full ingest takes < 1 min, so it's still not a long time
    # for last accessed to get into the Activity Stream

    user = UserFactory(email="test@a.com", email_list=["test@b.com", "test@c.com"])
    time.sleep(1)

    host = "localhost:8080"
    path = reverse("api-v1:core:activity-stream")

    response_1 = hawk_request(api_client, host, path)
    assert response_1.status_code == 200
    response_1_dict = response_1.json()

    assert len(response_1_dict["orderedItems"]) == 1

    middleware = UpdatedLastAccessedMiddleware(get_response=mocker.MagicMock())
    request = rf.get("/")
    request.user = user
    middleware(request)

    time.sleep(1)

    next_str = response_1_dict["next"]
    next_url = urllib.parse.urlsplit(next_str)
    assert next_url.netloc == host

    response_2 = hawk_request(
        api_client, host, next_url.path + (f"?{next_url.query}" if next_url.query else "")
    )
    response_2_dict = response_2.json()
    assert response_2_dict["orderedItems"] == []


def hawk_auth_header(key_id, secret_key, url, method, content, content_type):
    return mohawk.Sender(
        {
            "id": key_id,
            "key": secret_key,
            "algorithm": "sha256",
        },
        url,
        method,
        content=content,
        content_type=content_type,
    ).request_header


def hawk_request(api_client, host, path):
    url = f"http://{host}{path}"
    return api_client.get(
        path,
        content_type=None,
        HTTP_HOST="localhost:8080",
        HTTP_AUTHORIZATION=hawk_auth_header("the-id", "the-secret", url, "GET", b"", ""),
    )
