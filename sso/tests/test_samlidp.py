import os
import pytest

from django.urls import reverse

from sso.samlidp.models import SamlApplication
from sso.samlidp.processors import (
    AWSProcessor,
    EmailIdProcessor,
    GoogleProcessor,
    ModelProcessor,
)
from sso.tests.factories.saml import SamlApplicationFactory
from sso.tests.factories.user import (
    ApplicationPermissionFactory,
    AccessProfileFactory,
    ServiceEmailAddressFactory,
    UserFactory,
)


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

    @pytest.mark.parametrize('email, allowed_emails, expected', [
        ('me@testing.com', 'testing.com', True),
        ('me@testing.com', '', False),
        ('me@testing.com', '123testing.com ', False),
        ('me@testing.com', 'helloworld.com,testing.com,yolo.com', True),
    ])
    def test_has_access_by_email_domain(self, rf, email, allowed_emails, expected):
        SamlApplicationFactory(entity_id='an_entity_id', allow_access_by_email_suffix=allowed_emails)
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(email=email)

        assert processor.has_access(request) == expected

    def test_user_has_access_is_disabled(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')
        request.user = UserFactory(is_active=False)

        assert not processor.has_access(request)

    def test_get_service_email(self):

        ap = SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor(entity_id='an_entity_id')

        user = UserFactory(email='email1@testing.com', email_list=['extra1@testing.com'])
        user2 = UserFactory(email='email2@testing.com')

        ServiceEmailAddressFactory(user=user, saml_application=ap, email=user.emails.get(email='extra1@testing.com'))

        assert processor.get_service_email(user) == 'extra1@testing.com'
        assert not processor.get_service_email(user2)

    def test_get_user_id(self):
        user = UserFactory(email='email1@testing.com')

        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor(entity_id='an_entity_id')

        assert processor.get_user_id(user) == user.email

    def test_get_user_id_with_service_override(self):

        service_email = 'another@test.com'

        user = UserFactory(email='email1@testing.com', email_list=[service_email, 'testing123@testing.com'])

        ap = SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor(entity_id='an_entity_id')

        ServiceEmailAddressFactory(user=user, saml_application=ap, email=user.emails.get(email=service_email))

        assert processor.get_user_id(user) == service_email

    def test_user_id_field(self):
        user = UserFactory(email='email@testing.com', contact_email='testing@test.com')

        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor(entity_id='an_entity_id')

        processor.USER_ID_FIELD = 'contact_email'

        assert processor.get_user_id(user) == user.contact_email

    def test_user_id_field_uses_email_if_contact_email_is_empty(self):

        user = UserFactory(email='email@testing.com', contact_email='')

        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor(entity_id='an_entity_id')

        processor.USER_ID_FIELD = 'contact_email'

        assert not user.contact_email
        assert processor.get_user_id(user) == user.email


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

    def test_role_session_name_can_be_overridden(self):
        user = UserFactory()

        app = SamlApplicationFactory(entity_id='an_entity_id')
        processor = AWSProcessor(entity_id='an_entity_id')

        email = user.emails.first()

        user.service_emails.create(email=user.emails.first(), saml_application=app)

        identity = processor.create_identity(user, {}, role='test_role')

        assert identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] == email.email


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

        processor = EmailIdProcessor(entity_id='an_entity_id')
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


class TestIdpInitiatedLogin:
    def test_alias_entry(self, client, settings):

        settings.SAML_IDP_CONFIG['metadata']['local'] = [
            os.path.join(settings.SAML_IDP_CONFIG_DIR, 'sp_metadata.xml')
        ]

        settings.SAML_IDP_SPCONFIG = {
            'an-alias': {
                'entity_id': 'http://test-idp'
            }
        }

        saml_application = SamlApplicationFactory(entity_id='http://test-idp')

        access_profile = AccessProfileFactory(saml_apps_list=[saml_application])

        credentials = {
            'email': 'test1@test.com',
            'password': 'testing123',
        }

        user = UserFactory(**credentials, add_access_profiles=[access_profile])
        user.set_password(user.password)
        user.save()

        assert client.login(**credentials)

        url = reverse('saml_idp_init') + '?sp=an-alias&RelayState=http://testing123.com'

        response = client.get(url)

        assert b'<form action="http://localhost:7000/saml2/acs/" method="post">' in response.content
        assert b'<input type="hidden" name="RelayState" value="http://testing123.com"/>' in response.content
