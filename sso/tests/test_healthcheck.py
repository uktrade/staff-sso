import re
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

pytestmark = [pytest.mark.django_db]


class TestHealthCheck:
    def test_check_view(self, client):

        response = client.get(reverse("healthcheck"))

        assert response.status_code == 200

        xml = ET.fromstring(response.content)
        status = xml[0].text
        response_time = xml[1].text

        assert status == "OK"
        assert re.match("^[\d\.]+$", response_time)

    @patch(
        "sso.healthcheck.views.get_user_model",
        MagicMock(side_effect=Exception("something bad happened")),
    )
    def test_check_view_broken_database(self, client):

        response = client.get(reverse("healthcheck"))

        assert response.status_code == 200

        xml = ET.fromstring(response.content)
        status = xml[0].text

        assert status == "FAIL"
