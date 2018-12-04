import pytest

from sso.tests.factories.saml import SamlApplicationFactory
from sso.tests.factories.user import UserFactory
from sso.samlidp.processors import ModelProcessor, AWSProcessor
from sso.samlidp.models import SamlApplication


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


class TestAWSProcessor:
    def test_create_identity_role_is_provided(self, settings):
        user = UserFactory()

        app = SamlApplicationFactory(entity_id='an_entity_id')
        processor = AWSProcessor(entity_id='an_entity_id')

        identity = processor.create_identity(user, {}, role='test_role')

        assert identity['https://aws.amazon.com/SAML/Attributes/Role'] == 'test_role'

    def test_create_identity_user_id_is_provided(self):
        user = UserFactory()

        app = SamlApplicationFactory(entity_id='an_entity_id')
        processor = AWSProcessor(entity_id='an_entity_id')

        identity = processor.create_identity(user, {}, role='test_role')

        assert identity['https://aws.amazon.com/SAML/Attributes/RoleSessionName'] == str(user.user_id)


