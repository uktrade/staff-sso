import logging
import time

from googleapiclient.errors import HttpError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from .sync_with_google import get_google_client, http_retry

from sso.user.models import AccessProfile

from sso.samlidp.processors import build_google_user_id


logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync user accounts with MI Google'

    def __init__(self, *args, **kwargs):
        self.service = get_google_client()

        super().__init__(*args, **kwargs)

    @http_retry()
    def _create_group(self, group_name):

        group_email = '{}@{}'.format(group_name, settings.MI_GOOGLE_EMAIL_DOMAIN)
        body = {
            'email': group_email,
            'name': group_name,
            'description': 'Created automatically by staff-sso.',
            'adminCreated': True,
        }
        self.service.groups().insert(body=body).execute()

    @http_retry()
    def _get_groups(self):
        response = self.service.groups().list(domain=settings.MI_GOOGLE_EMAIL_DOMAIN).execute()

        return response['groups']

    @http_retry()
    def _get_group_members(self, group_name):
        group_email = '{}@{}'.format(group_name, settings.MI_GOOGLE_EMAIL_DOMAIN)
        users = []

        next_page_token = None
        while True:
            results = self.service.members().list(groupKey=group_email, pageToken=next_page_token).execute()

            members = results.get('members', [])
            next_page_token = results.get('nextPageToken', None)

            for member in members:
                users.append(member['email'])

            if not next_page_token:
                break

        return users

    @http_retry()
    def _remove_user_from_group(self, group_name, user_email):
        group_email = '{}@{}'.format(group_name, settings.MI_GOOGLE_EMAIL_DOMAIN)

        self.service.members().delete(groupKey=group_email, memberKey=user_email).execute()

    @http_retry()
    def _add_user_to_group(self, group_name, user_email):
        group_email = '{}@{}'.format(group_name, settings.MI_GOOGLE_EMAIL_DOMAIN)

        body = {
            'email': user_email,
        }

        self.service.members().insert(groupKey=group_email, body=body).execute()

    def handle(self, *args, **kwargs):

        start_time = time.time()
        self.stdout.write('Start time %s' % timezone.now().strftime('%X'))

        active_groups = [group['name'] for group in self._get_groups()]

        # ensure that google groups mirror staff-sso access profiles
        for ap in AccessProfile.objects.filter(
                    saml2_applications__slug=settings.MI_GOOGLE_USER_SYNC_SAML_APPLICATION_SLUG):
            if ap.slug not in active_groups:
                self._create_group(ap.slug)

        for group_name in active_groups:
            # NOTE if a group is created by the code above it can take a few minutes before it is active on google's
            # systems. So we purposely aren't attempting to add/remove users to this group. This will happen the
            # next time the script is run.

            users_in_group = self._get_group_members(group_name)

            for user in User.objects.filter(access_profiles__slug=group_name).distinct():
                google_email = build_google_user_id(user)

                if google_email not in users_in_group:
                    self.stdout.write(f'Adding {google_email} to {group_name}')
                    try:
                        self._add_user_to_group(group_name, google_email)
                    except HttpError as ex:
                        if ex.resp.status != 409:
                            # A 409 response indicates users that the user is already member of the group
                            raise

                else:
                    users_in_group.pop(users_in_group.index(google_email))

            for email in users_in_group:
                self.stdout.write(f'Removing {email} from {group_name}')
                self._remove_user_from_group(group_name, email)

        took = (time.time() - start_time)
        self.stdout.write('Took %0.2f' % took)
