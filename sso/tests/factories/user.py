import factory


class GroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Group {n+1}')

    class Meta:
        model = 'auth.Group'


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'user{n+1}@example.com')
    first_name = factory.Sequence(lambda n: f'Name {n+1}')
    last_name = factory.Sequence(lambda n: f'Surname {n+1}')

    class Meta:
        model = 'user.User'

    @factory.post_generation
    def email_list(self, create, extracted, **kwargs):
        """Add in a list of emails to build related user.emails"""
        if not create:
            return

        if extracted:
            for email in extracted:
                self.emails.create(email=email)

    @factory.post_generation
    def application_permission_list(self, create, extracted, **kwargs):

        if not create:
            return

        if extracted:
            for app in extracted:
                self.application_permissions.add(app)

    @factory.post_generation
    def add_access_profiles(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for profile in extracted:
                self.access_profiles.add(profile)


class AccessProfileFactory(factory.django.DjangoModelFactory):
    slug = factory.Sequence(lambda n: f'access-profile-{n+1}')
    name = factory.Sequence(lambda n: f'access profile {n+1}')

    @factory.post_generation
    def saml_apps_list(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for app in extracted:
                self.saml2_applications.add(app)

    @factory.post_generation
    def oauth_apps_list(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for app in extracted:
                self.oauth2_applications.add(app)

    class Meta:
        model = 'user.AccessProfile'


class ApplicationPermissionFactory(factory.django.DjangoModelFactory):
    permission = factory.Sequence(lambda n: f'permission{n+1}')

    class Meta:
        model = 'user.ApplicationPermission'


class ServiceEmailAddressFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'user.ServiceEmailAddress'
