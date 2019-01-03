import hashlib
import logging
import random
import secrets
import string
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client import client, file, tools
from sso.samlidp.processors import build_google_user_id


logger = logging.getLogger(__name__)

User = get_user_model()

SCOPES = 'https://www.googleapis.com/auth/admin.directory.user'


def get_google_client():
    # TODO: migrate to a service account configuration

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('admin', 'directory_v1', http=creds.authorize(Http()))

    return service


def http_retry(max_attempts=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except HttpError as ex:
                    attempts += 1
                    if ex.resp.status == 403:
                        if attempts < max_attempts:
                            delay = 2.0 ** attempts + random.randint(0, 999) / 1000
                            logger.warning(
                                'Tried %s %d times; retrying in %0.2f; exception: %s',
                                getattr(func, '__name__', 'no name'),
                                attempts,
                                delay,
                                str(ex)
                            )
                            time.sleep(delay)
                        else:
                            logger.error(
                                'Tried %s %d times; exception: %s; giving up',
                                getattr(func, '__name__', 'no name'),
                                attempts,
                                str(ex)
                            )

                            raise
                    else:
                        raise

        return wrapper

    return decorator


class Command(BaseCommand):
    help = 'Sync user accounts with MI Google'

    @http_retry()
    def _get_google_users(self, service):

        user_dict = {}
        next_page_token = None
        while True:
            results = service.users().list(
                customer='my_customer', orderBy='email', pageToken=next_page_token).execute()

            users = results.get('users', [])
            next_page_token = results.get('nextPageToken', None)

            for user in users:
                user_dict[user['primaryEmail']] = {
                    'id': user['id'],
                    'suspended': user['suspended'],
                    'processed': False,
                    'is_admin': user['isAdmin'],
                }

            if not next_page_token:
                break

        return user_dict

    @http_retry()
    def _disable_user(self, service, id):
        service.users().update(userKey=id, body={'suspended': 'true'})

    @http_retry()
    def _enable_user(self, service, id):
        service.users().update(userKey=id, body={'suspended': 'false'})

    @http_retry()
    def _create_user(self, service, primary_email, user):
        password = ''.join([secrets.choice(string.printable) for _ in range(random.randint(30, 50))]).encode('utf-8')

        template = {
            'primaryEmail': primary_email,
            'name': {
                'givenName': user.first_name,
                'familyName': user.last_name,
                'fullName': user.get_full_name()
            },
            'password': hashlib.sha1(password).hexdigest(),
            'hashFunction': 'SHA-1',
            'suspended': False
        }

        service.users().insert(body=template).execute()

    def _get_email(self, user):
        """
        The user entry in staff-sso needs to a suitable alternative email
        """

        return build_google_user_id(user.email)

    def handle(self, *args, **kwargs):
        start_time = time.time()
        self.stdout.write('Start time %s' % timezone.now().strftime('%X'))

        service = get_google_client()

        google_users = self._get_google_users(service)

        local_users = User.objects.filter(
            access_profiles__name__in=[settings.MI_USER_SYNC_ACCESS_PROFILE_NAME])

        for user in local_users:
            remote_email = self._get_email(user)

            logger.info('remote email: %s', remote_email)

            if remote_email not in google_users:
                self.stdout.write('{} does not exist in staff-sso; deactivating'.format(user.email))
                self._create_user(user, remote_email)

            elif remote_email in google_users and google_users['remote_email']['is_admin']:
                self.stdout.write('{} is an admin; doing nothing.'.format(user.email))

            elif google_users[remote_email]['suspended']:
                self.stdout.write('{} is enabled in staff-sso, but not not google; re-enabling account'.format(
                    user.email))
                self._enable_user(user['id'])

            if remote_email in google_users:
                google_users[remote_email]['processed'] = True

        # deactivate all users in google identity that aren't in staff-sso
        for email, user in google_users.items():
            if not user['processed'] and not user['is_admin']:
                self.stdout.write('{} does not exist in staff-sso; deactivating'.format(email))
                self._disable_user(user['id'])

        took = (time.time() - start_time)
        self.stdout.write('Took %0.2f' % took)
