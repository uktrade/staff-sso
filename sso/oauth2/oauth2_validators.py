from oauth2_provider.oauth2_validators import OAuth2Validator


class CustomOAuth2Validator(OAuth2Validator):
    def _get_base_data(self, request):
        return {
            "sub": request.user.email_user_id,
            "email": request.user.email,
            "user_id": str(request.user.user_id),
            "email_user_id": request.user.email_user_id,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        }

    def get_additional_claims(self, request):
        return self._get_base_data(request)

    def get_userinfo_claims(self, request):
        claims = {**super().get_userinfo_claims(request), **self._get_base_data(request)}

        return claims
