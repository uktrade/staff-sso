import logging

from django.shortcuts import redirect

from oauth2_provider.exceptions import OAuthToolkitError
from oauth2_provider.models import get_application_model
from oauth2_provider.scopes import get_scopes_backend
from oauthlib.oauth2.rfc6749.errors import AccessDeniedError

from oauth2_provider.views.base import AuthorizationView

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
