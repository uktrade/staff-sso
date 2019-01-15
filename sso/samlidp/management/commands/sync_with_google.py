import hashlib
import json
import logging
import random
import secrets
import string
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from sso.samlidp.processors import build_google_user_id


logger = logging.getLogger(__name__)

User = get_user_model()

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']


def get_google_client():
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(settings.MI_GOOGLE_SERVICE_ACCOUNT_DATA),
        scopes=SCOPES,
        subject=settings.MI_GOOGLE_SERVICE_ACCOUNT_DELEGATED_USER
    )

    service = build('admin', 'directory_v1', credentials=credentials, cache_discovery=False)

    return service


def http_retry(max_attempts=5):
    RETRY_REASONS = ['dailyLimitExceeded', 'userRateLimitExceeded', 'quotaExceeded']

    def _extract_reason(ex):
        if ex.resp.get('content-type', '').startswith('application/json'):
            return json.loads(ex.content).get('error').get('errors')[0].get('reason')

    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except HttpError as ex:
                    attempts += 1
                    if ex.resp.status == 403 and _extract_reason(ex) in RETRY_REASONS:
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

    def add_arguments(self, parser):

        parser.add_argument(
            '--inactive-accounts',
            choices=['noop', 'disable', 'delete'],
            dest='inactive_account_action',
            default='noop',
            help='What action to take with google accounts that exist '
                 'in google but are not enabled in staff-sso (noop = do nothing, the default action)',
        )

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
    def _delete_user(self, service, id):
        service.users().delete(userKey=id).execute()

    @http_retry()
    def _disable_user(self, service, id):
        service.users().update(userKey=id, body={'suspended': 'true'}).execute()

    @http_retry()
    def _enable_user(self, service, id):
        service.users().update(userKey=id, body={'suspended': 'false'}).execute()

    @http_retry()
    def _create_user(self, service, user, primary_email):
        password = ''.join([secrets.choice(string.printable) for _ in range(random.randint(30, 50))]).encode('utf-8')

        template = {
            'primaryEmail': primary_email,
            'name': {
                'givenName': user.first_name or 'unspecified',
                'familyName': user.last_name or 'unspecified',
                'fullName': user.get_full_name(),
            },
            'password': hashlib.sha1(password).hexdigest(),
            'hashFunction': 'SHA-1',
            'suspended': False
        }

        service.users().insert(body=template).execute()

    def handle(self, *args, inactive_account_action='noop', **kwargs):

        start_time = time.time()
        self.stdout.write('Start time %s' % timezone.now().strftime('%X'))

        service = get_google_client()

        google_users = self._get_google_users(service)

        local_users = User.objects.filter(
            access_profiles__slug__in=settings.MI_GOOGLE_USER_SYNC_ACCESS_PROFILES)

        for user in local_users:
            remote_email = build_google_user_id(user)

            logger.info('remote email: %s', remote_email)

            remote_user = google_users.get(remote_email, None)

            if not remote_user:
                self.stdout.write('{} does not exist in google; creating'.format(user.email))
                self._create_user(service, user, remote_email)

            elif remote_user and remote_user['is_admin']:
                self.stdout.write('{} is an admin; doing nothing.'.format(user.email))

            elif remote_user['suspended']:
                self.stdout.write('{} is enabled in staff-sso, but not not google; re-enabling account'.format(
                    user.email))
                self._enable_user(service, remote_user['id'])

            if remote_user:
                remote_user['processed'] = True

        # deactivate all users in google identity that aren't in staff-sso
        for email, remote_user in google_users.items():
            if not remote_user['processed'] and not remote_user['is_admin']:
                if inactive_account_action == 'disable':
                    self.stdout.write('{} does not exist in staff-sso; disabling'.format(email))
                    self._disable_user(service, remote_user['id'])
                elif inactive_account_action == 'delete':
                    self.stdout.write('{} does not exist in staff-sso; deleting'.format(email))
                    self._delete_user(service, remote_user['id'])
                else:
                    self.stdout.write('{} does not exist in staff-sso; noop'.format(email))

        took = (time.time() - start_time)
        self.stdout.write('Took %0.2f' % took)
