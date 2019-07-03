import pytest

from sso.samlidp.management.commands.sync_google_groups import Command

from .factories.saml import SamlApplicationFactory
from .factories.user import AccessProfileFactory, UserFactory

pytestmark = [
    pytest.mark.django_db
]


def test_groups_are_created(settings, mocker):
    mocker.patch('sso.samlidp.management.commands.sync_google_groups.get_google_client')
    slug = 'a-test-saml-application'
    settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = slug

    ap1 = AccessProfileFactory(saml_apps_list=[
        SamlApplicationFactory(slug=slug)])

    # access profile does not contain required saml application so won't be created
    AccessProfileFactory(saml_apps_list=[
        SamlApplicationFactory(slug='not-synced')])

    command = Command()

    command._get_groups = mocker.Mock(return_value=[])
    command._create_group = mocker.Mock()

    command.handle()

    command._create_group.assert_called_once_with(ap1.slug)


def test_groups_are_not_created_if_they_already_exist(settings, mocker):
    mocker.patch('sso.samlidp.management.commands.sync_google_groups.get_google_client')
    slug = 'a-test-saml-application'
    settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = slug

    ap = AccessProfileFactory(saml_apps_list=[
        SamlApplicationFactory(slug=slug)])

    command = Command()

    command._get_groups = mocker.Mock(return_value=[{'name': ap.slug}])
    command._create_group = mocker.Mock()
    command._get_group_members = mocker.Mock(return_value=[])

    command.handle()

    command._create_group.assert_not_called()


def test_user_is_added_to_group(settings, mocker):
    mocker.patch('sso.samlidp.management.commands.sync_google_groups.get_google_client')
    slug = 'a-test-saml-application'
    settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = slug
    settings.MI_GOOGLE_EMAIL_DOMAIN = 'test-email.com'

    ap = AccessProfileFactory(saml_apps_list=[
        SamlApplicationFactory(slug=slug)])

    UserFactory(email='mr.smith@example.com', add_access_profiles=[ap])

    command = Command()

    command._get_groups = mocker.Mock(return_value=[{'name': ap.slug}])
    command._create_group = mocker.Mock()
    command._get_group_members = mocker.Mock(return_value=[])
    command._add_user_to_group = mocker.Mock()

    command.handle()

    command._add_user_to_group.assert_called_once_with(ap.slug, 'mr.smith@test-email.com')


def test_user_is_removed_from_group(settings, mocker):
    mocker.patch('sso.samlidp.management.commands.sync_google_groups.get_google_client')
    slug = 'a-test-saml-application'
    settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG = slug
    settings.MI_GOOGLE_EMAIL_DOMAIN = 'test-email.com'

    ap = AccessProfileFactory(saml_apps_list=[
        SamlApplicationFactory(slug=slug)])

    command = Command()

    command._get_groups = mocker.Mock(return_value=[{'name': ap.slug}])
    command._create_group = mocker.Mock()
    command._get_group_members = mocker.Mock(return_value=['mr.smith@test-email.com'])
    command._remove_user_from_group = mocker.Mock()

    command.handle()

    command._remove_user_from_group.assert_called_once_with(ap.slug, 'mr.smith@test-email.com')
