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

from sso.core.logging import create_x_access_log

log = logging.getLogger('oauth2_provider')


class CustomAuthorizationView(AuthorizationView):

    def get(self, request, *args, **kwargs):
        """
        Overridden django-oauth-toolkit authorization view which checks that authenticated users are in the correct
        group to access the resource.
        """

        try:
            scopes, credentials = self.validate_authorization_request(request)
        except OAuthToolkitError as error:
            # Application is not available at this time.
            return self.error_response(error, application=None)

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

        try:
            uri, headers, body, status = self.create_authorization_response(
                request=self.request, scopes=' '.join(scopes),
                credentials=credentials, allow=allow)

            create_x_access_log(request, 200, oauth2_application=application.name)

            return redirect(uri)
        except OAuthToolkitError as error:
            if isinstance(error.oauthlib_error, AccessDeniedError):

                create_x_access_log(request, 403, oauth2_application=application.name)

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

    def get_introspecting_application(self):
        token = self.request.META['HTTP_AUTHORIZATION'][7:]

        return get_access_token_model().objects.get(token=token).application

    def get_token_response(self, token_value=None):

        introspecting_application = self.get_introspecting_application()

        try:
            token = get_access_token_model().objects.get(token=token_value)
        except ObjectDoesNotExist:
            return self._access_denied()

        if not token.is_valid():
            return HttpResponse(content=json.dumps({
                'active': False,
            }), status=200, content_type='application/json')

        assert token.application is not None

        result = {}
        if token.application == introspecting_application:
            result['access_type'] = 'client'
        elif token.application in introspecting_application.allow_tokens_from.all():
            result.update({
                'access_type': 'cross_client',
                'source_name': introspecting_application.name,
                'source_client_id': introspecting_application.client_id
            })
        else:
            return self._access_denied()

        result.update({
            'active': True,
            'scope': token.scope,
            'exp': int(calendar.timegm(token.expires.timetuple())),
            'client_id': token.application.client_id
        })
        if token.user:
            result['username'] = token.user.get_application_username(token.application)
            result['user_id'] = str(token.user.user_id)

        return HttpResponse(content=json.dumps(result), status=200, content_type='application/json')
