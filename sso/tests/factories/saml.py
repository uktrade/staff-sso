import datetime

from django.utils import timezone

import factory

from sso.samlidp.models import SamlApplication


class SamlApplicationFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'saml application {n+1}')
    start_url = factory.Sequence(lambda n: f'https://www.site{n+1}')
    entity_id = factory.Sequence(lambda n: f'entity_id_{n+1}')
    metadata_expiration_dt = timezone.now() + datetime.timedelta(days=356)
    allowed_ips = ''
    enabled = True

    class Meta:
        model = SamlApplication
