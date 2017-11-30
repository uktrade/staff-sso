import logging
from datetime import timedelta
from oauth2_provider.oauth2_validators import OAuth2Validator, Application, AccessToken, Grant, RefreshToken

from django.db import transaction
from django.utils import timezone
from django.conf import settings as django_settings

# from oauth2_provider.models import (
#     get_access_token_model,
#     get_application_model, get_grant_model, get_refresh_token_model
# )
from oauth2_provider.exceptions import FatalClientError
from oauth2_provider.settings import oauth2_settings

from .ip_check import is_trusted_ip

log = logging.getLogger("oauth2_provider")


class CustomOAuth2Validator(OAuth2Validator):
    @transaction.atomic
    def save_bearer_token(self, token, request, *args, **kwargs):
        """
        Save access and refresh token, If refresh token is issued, remove or
        reuse old refresh token as in rfc:`6`
        @see: https://tools.ietf.org/html/draft-ietf-oauth-v2-31#page-43
        """

        if "scope" not in token:
            raise FatalClientError("Failed to renew access token: missing scope")

        # trusted IPs (e.g. IPs from secure networks) are allowed to persist for longer
        if is_trusted_ip(request):
            expires_in_seconds = django_settings.OAUTH2_TRUSTED_ACCESS_TOKEN_EXPIRE_SECONDS
        else:
            expires_in_seconds = oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS

        expires = timezone.now() + timedelta(seconds=expires_in_seconds)

        if request.grant_type == "client_credentials":
            request.user = None

        # This comes from OAuthLib:
        # https://github.com/idan/oauthlib/blob/1.0.3/oauthlib/oauth2/rfc6749/tokens.py#L267
        # Its value is either a new random code; or if we are reusing
        # refresh tokens, then it is the same value that the request passed in
        # (stored in `request.refresh_token`)
        refresh_token_code = token.get("refresh_token", None)

        if refresh_token_code:
            # an instance of `RefreshToken` that matches the old refresh code.
            # Set on the request in `validate_refresh_token`
            refresh_token_instance = getattr(request, "refresh_token_instance", None)

            # If we are to reuse tokens, and we can: do so
            if not self.rotate_refresh_token(request) and \
                isinstance(refresh_token_instance, RefreshToken) and \
                    refresh_token_instance.access_token:

                access_token = AccessToken.objects.select_for_update().get(
                    pk=refresh_token_instance.access_token.pk
                )
                access_token.user = request.user
                access_token.scope = token["scope"]
                access_token.expires = expires
                access_token.token = token["access_token"]
                access_token.application = request.client
                access_token.save()

            # else create fresh with access & refresh tokens
            else:
                # revoke existing tokens if possible
                if isinstance(refresh_token_instance, RefreshToken):
                    try:
                        refresh_token_instance.revoke()
                    except (AccessToken.DoesNotExist, RefreshToken.DoesNotExist):
                        pass
                    else:
                        setattr(request, "refresh_token_instance", None)

                access_token = self._create_access_token(expires, request, token)

                refresh_token = RefreshToken(
                    user=request.user,
                    token=refresh_token_code,
                    application=request.client,
                    access_token=access_token
                )
                refresh_token.save()

        # No refresh token should be created, just access token
        else:
            self._create_access_token(expires, request, token)

        # TODO: check out a more reliable way to communicate expire time to oauthlib
        token["expires_in"] = expires_in_seconds

