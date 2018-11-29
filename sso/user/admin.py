from django import forms
from django.contrib import admin
from django.forms.widgets import CheckboxSelectMultiple
from django.forms import ModelForm
from django.utils.safestring import mark_safe
from django.urls import reverse

from oauth2_provider.admin import ApplicationAdmin as OAuth2ApplicationAdmin, Application

from .filter import ApplicationFilter
from .models import EmailAddress, User, AccessProfile
from sso.oauth2.models import Application


class UserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['permitted_applications'].widget = CheckboxSelectMultiple()
        self.fields['permitted_applications'].queryset = Application.objects.all()
        self.fields['permitted_applications'].help_text = ''
        self.fields['access_profiles'].widget = CheckboxSelectMultiple()
        self.fields['access_profiles'].queryset = AccessProfile.objects.all()
        self.fields['access_profiles'].help_text = ''

    class Meta:
        model = User
        fields = '__all__'


class EmailInline(admin.TabularInline):
    model = EmailAddress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('emails__email', 'email', 'first_name', 'last_name')
    list_filter = (ApplicationFilter, 'is_superuser')
    fields = ('user_id', 'email', 'first_name', 'last_name', 'is_superuser',
              'date_joined', 'last_login', 'last_accessed', 'access_profiles', 'permitted_applications')
    readonly_fields = ('date_joined', 'last_login', 'last_accessed', 'user_id')
    list_display = ('email', 'email_list', 'is_superuser', 'last_login', 'last_accessed', 'list_permitted_applications',
                    'list_access_profiles', 'show_permissions_link')
    inlines = [
        EmailInline
    ]

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = UserForm
        return super().get_form(request, obj, **kwargs)

    def list_permitted_applications(self, obj):
        return ', '.join(obj.permitted_applications.all().values_list('name', flat=True))

    list_permitted_applications.short_description = 'permitted applications'

    def list_access_profiles(self, obj):
        return ', '.join(obj.access_profiles.all().values_list('name', flat=True))

    list_access_profiles.short_description = 'access profiles'

    def email_list(self, obj):
        return ', '.join(obj.emails.all().values_list('email', flat=True))

    def show_permissions_link(self, obj):
        return mark_safe('<a href="{}" target="_blank">show perms</a>'.format(
            reverse('show-permissions-view', kwargs={'user_id': obj.id})
        ))

    show_permissions_link.short_description = ' '


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


@admin.register(AccessProfile)
class AccessProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'list_oauth2_applications')

    def list_oauth2_applications(self, obj):
        return ', '.join([str(app) for app in obj.oauth2_applications.all()])

    list_oauth2_applications.short_description = 'OAuth2 Applications'
