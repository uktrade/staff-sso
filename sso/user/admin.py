from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.forms.widgets import CheckboxSelectMultiple
from django.urls import reverse
from django.utils.html import format_html_join, format_html, escape
from django.utils.safestring import mark_safe

from oauth2_provider.admin import ApplicationAdmin as OAuth2ApplicationAdmin

from sso.oauth2.models import Application
from sso.usersettings.models import UserSettings
from .filter import ApplicationFilter
from .models import AccessProfile, EmailAddress, User


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
    readonly_fields = ('last_login',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('/static/stylesheets/admin.css',)
        }

    search_fields = ('emails__email', 'email', 'first_name', 'last_name')
    list_filter = (ApplicationFilter, 'is_superuser')
    fields = ('user_id', 'email', 'first_name', 'last_name', 'date_joined', 'last_login', 'last_accessed',
              'access_profiles', 'permitted_applications', 'list_user_settings_wrapper')
    readonly_fields = ('date_joined', 'last_login', 'last_accessed', 'user_id', 'list_user_settings_wrapper')
    list_display = ('email', 'email_list', 'is_superuser', 'last_login', 'last_accessed',
                    'list_permitted_applications', 'list_access_profiles', 'show_permissions_link')
    inlines = [
        EmailInline
    ]

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = UserForm
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        if request.user.is_superuser:
            fields += ('is_staff', 'is_superuser', 'groups', 'user_permissions')
        return fields

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

    def list_user_settings(self, obj):
        return '<br>'.join(obj.usersettings_set.all().values_list('settings', flat=True))

    def list_user_settings_wrapper(self, obj):
        return format_html(
            '<div class="admin__readonly-wrapper--scroll">{}</div>',
            mark_safe(self.list_user_settings(obj))
        )

    list_user_settings_wrapper.short_description = 'User Settings'


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
    prepopulated_fields = {'slug': ('name',)}

    def list_oauth2_applications(self, obj):
        return ', '.join([str(app) for app in obj.oauth2_applications.all()])

    list_oauth2_applications.short_description = 'OAuth2 Applications'
