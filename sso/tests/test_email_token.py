from sso.emailauth.models import EmailToken
from sso.emailauth.forms import EmailForm


class TestEmailTokenModel:
    def test_extract_name_from_email(self):
        test_emails = [
            ['aaa.bbb.ccc@example.com', 'aaa', 'bbb ccc'],
            ['aaa@example.com', 'aaa', ''],
            ['aaa-bbb@example.com', 'aaa-bbb', ''],
            ['aaa.bbb@example.com', 'aaa', 'bbb']
        ]

        for email, first_name, last_name in test_emails:
            obj = EmailToken()
            obj.extract_name_from_email(email)
            assert obj.first_name == first_name, email
            assert obj.last_name == last_name, email


class TestEmailTokenForm:
    def test_extract_redirect_uri(self):
        next_url = '/o/authorize/?scope=introspection&state=kalle&redirect_uri=https://localhost:5000/authorised&response_type=code&client_id=0j855NJvxO1R3Ld5qDVRsZ1WaGEbSqjxbYRFcRcw' # noqa

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == 'https://localhost:5000'

    def test_extract_redirect_uri_missing_next_url(self):

        next_url = ''

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == ''

    def test_extract_redirect_uri_missing_redirect_uri_qs(self):

        next_url = 'a-random-url?a=b&b=c&no_redirect_uri=False'

        form = EmailForm()

        url = form.extract_redirect_url(next_url)

        assert url == next_url

