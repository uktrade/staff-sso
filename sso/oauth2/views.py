import calendar
import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.exceptions import OAuthToolkitError
from oauth2_provider.models import get_access_token_model
from oauth2_provider.views.base import AuthorizationView
from oauth2_provider.views.introspect import IntrospectTokenView
from oauthlib import oauth2

from sso.core.logging import create_x_access_log

log = logging.getLogger("oauth2_provider")


LAST_FAILED_APPLICATION_SESSION_KEY = "_last_failed_access_app"


class CustomAuthorizationView(AuthorizationView):
    def create_authorization_response(self, request, scopes, credentials, allow):

        application = self.oauth2_data["application"]

        if not request.user.can_access(application):
            # record the application so that we can prepulate this field
            #  on the access denied / contact us page
            request.session[LAST_FAILED_APPLICATION_SESSION_KEY] = application.name
            create_x_access_log(request, 403, oauth2_application=application.name)

            raise OAuthToolkitError(
                error=oauth2.AccessDeniedError(state=credentials.get("state", None)),
                redirect_uri=reverse("contact:access-denied"),
            )

        create_x_access_log(request, 200, oauth2_application=application.name)
        return super().create_authorization_response(request, scopes, credentials, allow)

    def redirect(self, redirect_to, application):
        # the base `redirect()` method is designed to redirect back to application;
        # however, we only redirect to the contact page
        return redirect(redirect_to)


@method_decorator(csrf_exempt, name="dispatch")
class CustomIntrospectTokenView(IntrospectTokenView):
    def _access_denied(self):
        return HttpResponse(
            content=json.dumps({"active": False}), status=401, content_type="application/json"
        )

    def get_introspecting_application(self):  # TODO(jf): get application from here
        token = self.request.META["HTTP_AUTHORIZATION"][7:]

        return get_access_token_model().objects.get(token=token).application

    def get_token_response(self, token_value=None):

        introspecting_application = self.get_introspecting_application()

        try:
            token = get_access_token_model().objects.get(token=token_value)
        except ObjectDoesNotExist:
            return self._access_denied()

        if not token.is_valid():
            return HttpResponse(
                content=json.dumps(
                    {
                        "active": False,
                    }
                ),
                status=200,
                content_type="application/json",
            )

        assert token.application is not None

        result = {}
        if token.application == introspecting_application:
            result["access_type"] = "client"
        elif token.application in introspecting_application.allow_tokens_from.all():
            result.update(
                {
                    "access_type": "cross_client",
                    "source_name": introspecting_application.name,
                    "source_client_id": introspecting_application.client_id,
                }
            )
        else:
            return self._access_denied()

        result.update(
            {
                "active": True,
                "scope": token.scope,
                "exp": int(calendar.timegm(token.expires.timetuple())),
                "client_id": token.application.client_id,
            }
        )
        if token.user:
            result["username"] = token.user.get_application_username(token.application)
            result["user_id"] = str(token.user.user_id)
            result["email_user_id"] = token.user.email_user_id

        return HttpResponse(content=json.dumps(result), status=200, content_type="application/json")
