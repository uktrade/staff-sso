import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Pytest fixture for Django REST framework ApiClient."""
    return APIClient()
