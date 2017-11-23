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
