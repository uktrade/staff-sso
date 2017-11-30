import pytest

from sso.oauth2.ip_check import is_trusted_ip, ip_in_range, is_cidr


class TestIPCheck:

    @pytest.mark.parametrize('ip_range,valid', [
        (['192.168.0.100/32'], True),
        (['192.168.0.0/24'], True),
        (['192.168.0.100'], True),
        (['192.168.0.200/32'], False),
        (['192.168.1.0/24'], False),
        (['192.168.0.101'], False),
    ])
    def test_ip_in_range(self, ip_range, valid):
        assert ip_in_range('192.168.0.100', trusted_ips=ip_range) == valid

    def test_is_trusted_ip(self, mocker):
        mocked = mocker.patch('sso.oauth2.ip_check.get_real_ip')
        mocked.return_value = '192.168.0.100'

        mocked_request = mocker.Mock()
        mocked_request.headers.return_value = {
            'REMOTE_ADDR': '192.168.0.1'
        }

        assert not is_trusted_ip(mocked_request, trusted_ips=['192.168.0.1/32'])
        assert is_trusted_ip(mocked_request, trusted_ips=['192.168.0.100/32'])

    def test_is_cidr(self):
        assert is_cidr('127.0.0.1/32')
        assert not is_cidr('127.0.0.1')
