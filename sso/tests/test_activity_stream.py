from django.urls import reverse
import pytest


def test(api_client):
    response = api_client.get(reverse('api-v1:core:activity-stream'))
    assert response.status_code == 200
    assert response.json() == {}
