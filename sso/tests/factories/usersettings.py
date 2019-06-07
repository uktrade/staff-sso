import factory
from faker import Faker

fake = Faker()


class UserSettingsFactory(factory.django.DjangoModelFactory):
    app_slug = factory.Sequence(lambda n: f'test-app-name-{n+1}')
    settings = factory.Sequence(lambda n: f'setting_parent.child-{n+1}:setting-{n+1}')

    class Meta:
        model = 'usersettings.UserSettings'
