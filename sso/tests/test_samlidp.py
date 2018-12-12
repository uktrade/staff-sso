import pytest

from sso.samlidp.models import SamlApplication
from sso.samlidp.processors import AWSProcessor, GoogleProcessor, ModelProcessor
from sso.tests.factories.saml import SamlApplicationFactory
from sso.tests.factories.user import UserFactory


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

    def test_is_application_enabled_true(self):
        SamlApplicationFactory(entity_id='an_entity_id', enabled=True)
        processor = ModelProcessor('an_entity_id')

        assert processor.is_enabled({})

    def test_is_application_enabled_false(self):
        SamlApplicationFactory(entity_id='an_entity_id', enabled=False)
        processor = ModelProcessor('an_entity_id')

        assert not processor.is_enabled({})

    def test_is_valid_ip_with_ip_restriction_disabled(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')

        assert processor.is_enabled(request)

    def test_is_enabled_ip_restriction_no_x_forwarded_header(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id', ip_restriction='1.1.1.1')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/')

        assert not processor.is_enabled(request)

    def test_is_enabled_ip_restriction_valid_ip(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id', ip_restriction='1.1.1.1')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')

        assert processor.is_enabled(request)

    def test__is_enabled_ip_restriction_ip_not_whitelisted(self, rf):
        SamlApplicationFactory(entity_id='an_entity_id', ip_restriction='8.8.8.8')
        processor = ModelProcessor('an_entity_id')

        request = rf.get('/whatever/', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2, 3.3.3.3')

        assert not processor.is_enabled(request)


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
    def test_preferred_email_is_supplied(self, settings):
        SamlApplicationFactory(entity_id='an_entity_id')
        settings.MI_GOOGLE_EMAIL_DOMAIN = '@test.com'

        user = UserFactory(email='hello@world.com', email_list=['testing@test.com'])

        processor = GoogleProcessor(entity_id='an_entity_id')

        assert processor.get_user_id(user) == 'testing@test.com'

    def test_preferred_email_provides_default_if_preferred_not_available(self, settings):
        SamlApplicationFactory(entity_id='an_entity_id')
        settings.SAML_IDP_DJANGO_USERNAME_FIELD = 'email'

        user = UserFactory(email='hello@world.com')

        processor = GoogleProcessor(entity_id='an_entity_id')

        assert processor.get_user_id(user) == 'hello@world.com'
