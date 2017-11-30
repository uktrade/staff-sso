import calendar
import logging
import json

from django.shortcuts import redirect
from django.http import HttpResponse

from django.core.exceptions import ObjectDoesNotExist
from oauth2_provider.models import get_access_token_model
from oauth2_provider.exceptions import OAuthToolkitError
from oauth2_provider.models import get_application_model
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
                return redirect('access-denied')
            else:
                return self.error_response(error)


class CustomIntrospectTokenView(IntrospectTokenView):
    @staticmethod
    def get_token_response(token_value=None):
        try:
            token = get_access_token_model().objects.get(token=token_value)
        except ObjectDoesNotExist:
            return HttpResponse(
                content=json.dumps({"active": False}),
                status=401,
                content_type="application/json"
            )
        else:
            if token.is_valid():
                data = {
                    "active": True,
                    "scope": token.scope,
                    "exp": int(calendar.timegm(token.expires.timetuple())),
                }
                if token.application:
                    data["client_id"] = token.application.client_id
                if token.user:
                    if not token.application:
                        data['username'] = token.user.get_username()
                    else:
                        data["username"], _ = token.user.get_emails_for_application(token.application)
                return HttpResponse(content=json.dumps(data), status=200, content_type="application/json")
            else:
                return HttpResponse(content=json.dumps({
                    "active": False,
                }), status=200, content_type="application/json")

