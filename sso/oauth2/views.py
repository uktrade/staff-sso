import calendar
import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.exceptions import OAuthToolkitError
from oauth2_provider.models import get_access_token_model, get_application_model
from oauth2_provider.scopes import get_scopes_backend
from oauth2_provider.views.base import AuthorizationView
from oauth2_provider.views.introspect import IntrospectTokenView
from oauthlib.oauth2.rfc6749.errors import AccessDeniedError

log = logging.getLogger('oauth2_provider')


class CustomAuthorizationView(AuthorizationView):

    def get(self, request, *args, **kwargs):
        """
        Overridden django-oauth-toolkit authorization view which checks that authenticated users are in the correct
        group to access the resource.
        """

        try:
            scopes, credentials = self.validate_authorization_request(request)
            all_scopes = get_scopes_backend().get_all_scopes()
            kwargs['scopes_descriptions'] = [all_scopes[scope] for scope in scopes]
            kwargs['scopes'] = scopes
            # at this point we know an Application instance with such client_id exists in the database

            # TODO: Cache this!
            application = get_application_model().objects.get(client_id=credentials['client_id'])

            kwargs['application'] = application
            kwargs['client_id'] = credentials['client_id']
            kwargs['redirect_uri'] = credentials['redirect_uri']
            kwargs['response_type'] = credentials['response_type']
            kwargs['state'] = credentials['state']

            assert request.user.is_authenticated

            # Check that the user has all of the application's groups
            allow = request.user.can_access(application)

            # remember which application the user tried to access so they can request
            # access on the access denied form.

            request.session.pop('_last_failed_access_app', None)
            if not allow:
                request.session['_last_failed_access_app'] = application.name

            self.oauth2_data = kwargs

            # following two loc are here only because of https://code.djangoproject.com/ticket/17795
            form = self.get_form(self.get_form_class())
            kwargs['form'] = form

            uri, headers, body, status = self.create_authorization_response(
                request=self.request, scopes=' '.join(scopes),
                credentials=credentials, allow=allow)

            return redirect(uri)

        except OAuthToolkitError as error:
            if isinstance(error.oauthlib_error, AccessDeniedError):
                return redirect('contact:access-denied')
            else:
                return self.error_response(error, application)


@method_decorator(csrf_exempt, name='dispatch')
class CustomIntrospectTokenView(IntrospectTokenView):
    def _access_denied(self):
        return HttpResponse(
            content=json.dumps({'active': False}),
            status=401,
            content_type='application/json'
        )

    def get_token_response(self, token_value=None):

        introspecting_application = \
            self.request.resource_owner.oauth2_provider_accesstoken.first().application

        try:
            token = get_access_token_model().objects.get(token=token_value)
        except ObjectDoesNotExist:
            return self._access_denied()
        else:
            if token.is_valid():
                data = {
                    'active': True,
                    'scope': token.scope,
                    'exp': int(calendar.timegm(token.expires.timetuple())),
                }
                if not token.application:
                    self._access_denied()
                else:
                    data['client_id'] = token.application.client_id

                if introspecting_application != token.application:
                    if introspecting_application in token.application.peers.all():
                        data['cross_client_token'] = 'yes'
                    else:
                        return self._access_denied()

                if token.user:
                    if not token.application:
                        data['username'] = token.user.get_username()
                    else:
                        data['username'], _ = token.user.get_emails_for_application(token.application)
                return HttpResponse(content=json.dumps(data), status=200, content_type='application/json')
            else:
                return HttpResponse(content=json.dumps({
                    'active': False,
                }), status=200, content_type='application/json')
