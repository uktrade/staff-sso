from django.contrib import admin
from oauth2_provider.models import get_access_token_model, get_application_model


AccessToken = get_access_token_model()
Application = get_application_model()


class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "application", "expires")
    raw_id_fields = ("user", "source_refresh_token")


class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "default_access_allowed",
        "allow_access_by_email_suffix",
        "allow_tokens_from_display",
    )
    raw_id_fields = ("user",)
    exclude = ("client_type", "authorization_grant_type", "skip_authorization")

    def allow_tokens_from_display(self, obj):
        return ", ".join(app.name for app in obj.allow_tokens_from.all())

    allow_tokens_from_display.short_description = "allow tokens from"


admin.site.unregister(AccessToken)
admin.site.register(AccessToken, AccessTokenAdmin)

admin.site.unregister(Application)
admin.site.register(Application, ApplicationAdmin)
