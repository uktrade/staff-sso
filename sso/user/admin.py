from django import forms
from django.contrib import admin
from oauth2_provider.admin import ApplicationAdmin as OAuth2ApplicationAdmin, Application

from .filter import ApplicationFilter
from .models import EmailAddress, User


class EmailInline(admin.TabularInline):
    model = EmailAddress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('emails__email',)
    list_filter = (ApplicationFilter, 'is_superuser')
    fields = ('email', 'first_name', 'last_name', 'is_superuser',
              'date_joined', 'last_login', 'last_accessed', 'permitted_applications')
    readonly_fields = ('date_joined', 'last_login')
    list_display = ('email', 'email_list', 'is_superuser', 'last_login', 'last_accessed', 'permitted_apps')
    inlines = [
        EmailInline
    ]

    def permitted_apps(self, obj):
        return ', '.join(obj.permitted_applications.all().values_list('name', flat=True))

    def email_list(self, obj):
        return ', '.join(obj.emails.all().values_list('email', flat=True))


class ApplicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            allowed_tokens_from = self.fields['allow_tokens_from']
            allowed_tokens_from.queryset = allowed_tokens_from.queryset.exclude(pk=self.instance.pk)

    class Meta:
        fields = '__all__'
        model = Application


admin.site.unregister(Application)


@admin.register(Application)
class ApplicationAdmin(OAuth2ApplicationAdmin):
    form = ApplicationForm
