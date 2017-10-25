from datetime import timedelta

import factory
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application

from .user import UserFactory


class ApplicationFactory(factory.django.DjangoModelFactory):
    client_type = Application.CLIENT_CONFIDENTIAL
    authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE
    skip_authorization = True
    name = 'Test oauth app'

    class Meta:
        model = Application

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        """Allow a list of users to be passed in"""
        if not create:
            return

        if extracted:
            for user in extracted:
                self.users.add(user)


class AccessTokenFactory(factory.django.DjangoModelFactory):
    application = factory.SubFactory(ApplicationFactory)
    token = factory.Sequence(lambda n: f'token{n+1}')
    user = factory.SubFactory(UserFactory)
    expires = timezone.now() + timedelta(days=1)
    scope = 'read'

    class Meta:
        model = AccessToken
