from django.urls import reverse
import pytest


def test_via_public_internet_then_403(api_client):
    response = api_client.get(reverse('api-v1:core:activity-stream'),
        HTTP_X_FORWARDED_FOR='',
    )
    assert response.status_code == 403
    assert response.json() == {}


def test_via_internal_networking_then_200(api_client):
    response = api_client.get(reverse('api-v1:core:activity-stream'))
    assert response.status_code == 200
