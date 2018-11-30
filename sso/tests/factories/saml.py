import factory

from sso.samlidp.models import SamlApplication


class SamlApplicationFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'saml application {n+1}')
    start_url = 'http://example.org'
    entity_id = factory.Sequence(lambda n: f'entity_id_{n+1}')
    ip_restriction = ''
    enabled = True

    class Meta:
        model = SamlApplication
