import re

from django.contrib import admin
from oauth2_provider.admin import ApplicationAdmin, Application

from .filter import ApplicationFilter
from .models import EmailAddress, User


class EmailInline(admin.TabularInline):
    model = EmailAddress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('emails__email', )
    list_filter = (ApplicationFilter, 'is_superuser')
    fields = ('email', 'first_name', 'last_name', 'is_superuser',
              'date_joined', 'last_login', 'permitted_applications')
    readonly_fields = ('date_joined', 'last_login')
    list_display = ('email', 'email_list', 'is_superuser', 'last_login', 'permitted_apps')
    inlines = [
        EmailInline
    ]

    def permitted_apps(self, obj):
        return ', '.join(obj.permitted_applications.all().values_list('name', flat=True))

    def email_list(self, obj):
        return ', '.join(obj.emails.all().values_list('email', flat=True))


admin.site.unregister(Application)


@admin.register(Application)
class ExtendedApplicationAdmin(ApplicationAdmin):
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "peer_applications":
            pk = re.match('.*/(\d+).*', request.path).groups()[-1]
            kwargs["queryset"] = Application.objects.exclude(pk=pk)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
