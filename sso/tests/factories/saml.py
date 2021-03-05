import datetime
import os

import factory
from django.utils import timezone

from sso.samlidp.models import SamlApplication


def _load_metadata(_):
    path = os.path.join(os.path.dirname(__file__), 'sp-saml.xml')
    with open(path) as fd:
        return fd.read()


class SamlApplicationFactory(factory.django.DjangoModelFactory):
    pretty_name = factory.Sequence(lambda n: f'saml application {n+1}')
    start_url = factory.Sequence(lambda n: f'https://www.site{n+1}')
    entity_id = factory.Sequence(lambda n: f'entity_id_{n+1}')
    metadata_expiration_dt = timezone.now() + datetime.timedelta(days=356)
    allowed_ips = ''
    metadata_expiration_dt = timezone.now() + datetime.timedelta(minutes=5)
    local_metadata = factory.LazyAttribute(_load_metadata)
    active = True

    class Meta:
        model = SamlApplication
