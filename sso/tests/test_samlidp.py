import pytest

from sso.samlidp.models import SamlApplication
from sso.samlidp.processors import AWSProcessor, EmailIdProcessor, GoogleProcessor, ModelProcessor
from sso.tests.factories.saml import SamlApplicationFactory
from sso.tests.factories.user import ApplicationPermissionFactory, AccessProfileFactory, UserFactory


pytestmark = [
    pytest.mark.django_db
]


class TestModelProcessor:
    def test_model_is_loaded(self):
        app = SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor('an_entity_id')

        assert processor._application == app

    def test_model_does_not_exist(self):
        with pytest.raises(SamlApplication.DoesNotExist):
            ModelProcessor('a_non_existent_entity_id')

    def test_has_access_application_enabled(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', enabled=True)
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        assert processor.has_access(request)

    def test_has_access_application_disabled(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', enabled=False)
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        assert not processor.has_access(request)

    def test_is_valid_ip_with_ip_restriction_disabled(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        assert processor.has_access(request)

    def test_has_access_ip_restriction_no_x_forwarded_header(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', allowed_ips='1.1.1.1')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        assert not processor.has_access(request)

    def test_has_access_ip_restriction_valid_ip(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', allowed_ips='1.1.1.1')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')
        request.user = UserFactory(add_access_profiles=[ap])

        assert processor.has_access(request)

    def test_has_access_ip_restriction_ip_not_whitelisted(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id', allowed_ips='8.8.8.8')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')
        request.user = UserFactory(add_access_profiles=[ap])

        assert not processor.has_access(request)

    def test_has_access_user_not_in_profile(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory()

        assert not processor.has_access(request)

    def test_user_has_access(self, rf):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])

        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        assert processor.has_access(request)

    def test_x_application_logging(self, rf, mocker):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id')
        ap = AccessProfileFactory(saml_apps_list=[saml_app])

        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(add_access_profiles=[ap])

        mock_create_x_access_log = mocker.patch('sso.samlidp.processors.create_x_access_log')

        processor.has_access(request)

        mock_create_x_access_log.assert_called_once_with(request, 200, application=saml_app.name)

    def test_x_application_logging_without_access(self, rf, mocker):
        saml_app = SamlApplicationFactory(entity_id='an_entity_id')

        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory()

        mock_create_x_access_log = mocker.patch('sso.samlidp.processors.create_x_access_log')

        processor.has_access(request)

        mock_create_x_access_log.assert_called_once_with(request, 403, application=saml_app.name)


class TestAWSProcessor:
    def test_create_identity_role_is_provided(self, settings):
        user = UserFactory()

        SamlApplicationFactory(entity_id='an_entity_id')
        processor = AWSProcessor(entity_id='an_entity_id')

        identity = processor.create_identity(user, {}, role='test_role')

        assert identity['https://aws.amazon.com/SAML/Attributes/Role'] == 'test_role'

    def test_create_identity_user_id_is_provided(self):
        user = UserFactory()

        SamlApplicationFactory(entity_id='an_entity_id')
        processor = AWSProcessor(entity_id='an_entity_id')

        identity = processor.create_identity(user, {}, role='test_role')

        assert identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] == str(user.user_id)


class TestGoogleProcessor:
    def test_correct_email_is_supplied(self, settings):
        SamlApplicationFactory(entity_id='an_entity_id')
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'test.com'

        user = UserFactory(email='hello@world.com')

        processor = GoogleProcessor(entity_id='an_entity_id')
        assert processor.get_user_id(user) == 'hello@test.com'

    def test_email_can_be_overridden(self, settings):
        SamlApplicationFactory(entity_id='an_entity_id')
        settings.MI_GOOGLE_EMAIL_DOMAIN = 'test.com'

        user = UserFactory(email='hello@world.com', email_list=[
            'hello_world@' + settings.MI_GOOGLE_EMAIL_DOMAIN
        ])

        processor = GoogleProcessor(entity_id='an_entity_id')
        assert processor.get_user_id(user) == 'hello_world@test.com'


class TestEmailIdProcessor:
    def test_email_id_is_supplied(self):
        SamlApplicationFactory(entity_id='an_entity_id')
        user = UserFactory(email='hello@world.com')

        processor = EmailIdProcessor()
        assert user.email_user_id == processor.get_user_id(user)

    def test_groups_are_supplied(self):
        app1 = SamlApplicationFactory(entity_id='an_entity_id')
        app2 = SamlApplicationFactory(entity_id='an_second_entity_id')

        ap1 = ApplicationPermissionFactory(saml2_application=app1)
        ap2 = ApplicationPermissionFactory(saml2_application=app1)
        ap3 = ApplicationPermissionFactory()
        ap4 = ApplicationPermissionFactory(saml2_application=app2)
        ApplicationPermissionFactory(saml2_application=app1)
        ApplicationPermissionFactory()
        ap7 = ApplicationPermissionFactory(saml2_application=app2)
        ap8 = ApplicationPermissionFactory(saml2_application=app1)

        processor = EmailIdProcessor(entity_id='an_entity_id')

        user = UserFactory(email='hello@world.com', application_permission_list=[ap1, ap3, ap4, ap8])
        UserFactory(email='goodbye@world.com', application_permission_list=[ap2, ap3, ap7])

        identity = processor.create_identity(user, {})

        assert set(identity['groups']) == {ap1.permission, ap8.permission}
