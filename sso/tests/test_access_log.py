import json

import pytest
from freezegun import freeze_time

from sso.core.logging import create_x_access_log
from sso.tests.factories.user import UserFactory


class TestAppAccessLog:
    @pytest.mark.django_db
    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_user_info_is_logged(self, rf, mocker):
        mock_logger = mocker.patch('sso.core.logging.logger')

        request = rf.get('/whatever/')

        create_x_access_log(request, 200)

        mock_logger.info.assert_called_once()
        assert json.loads(mock_logger.info.call_args[0][0]) == \
            {
                "request_id": "",
                "request_time": "2017-06-22T15:50:00",
                "sso_user_id": None,
                "local_user_id": None,
                "path": "/whatever/",
                "host": "testserver",
                "status": 200,
                "ip": None,
                "message": "",
                "service": "staff-sso test"
            }

    @pytest.mark.django_db
    @freeze_time('2017-06-22 15:50:00.000000+00:00')
    def test_log_without_user(self, rf, mocker):
        mock_logger = mocker.patch('sso.core.logging.logger')

        request = rf.get('/whatever/')
        user = UserFactory()
        request.user = user

        create_x_access_log(request, 200, message='test message')

        mock_logger.info.assert_called_once()
        assert json.loads(mock_logger.info.call_args[0][0]) == \
            {
                "request_id": "",
                "request_time": "2017-06-22T15:50:00",
                "sso_user_id": str(user.user_id),
                "local_user_id": user.id,
                "path": "/whatever/",
                "host": "testserver",
                "status": 200,
                "ip": None,
                "message": "test message",
                "service": "staff-sso test"
            }
