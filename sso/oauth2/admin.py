from django.contrib import admin
from oauth2_provider.models import get_access_token_model


AccessToken = get_access_token_model()


class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'application', 'expires')
    raw_id_fields = ('user', 'source_refresh_token')


admin.site.unregister(AccessToken)
admin.site.register(AccessToken, AccessTokenAdmin)
