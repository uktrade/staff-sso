from django.contrib import admin

from .filter import ApplicationFilter
from .models import EmailAddress, User


class EmailInline(admin.TabularInline):
    model = EmailAddress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('emails__email', )
    list_filter = (ApplicationFilter, 'is_superuser')
    fields = ('account_ref', 'email', 'first_name', 'last_name',  'is_superuser',
              'date_joined', 'last_login', 'permitted_applications')
    readonly_fields = ('account_ref', 'date_joined', 'last_login')
    list_display = ('email', 'email_list', 'is_superuser', 'last_login', 'permitted_apps')
    inlines = [
        EmailInline
    ]

    def permitted_apps(self, obj):
        return ', '.join(obj.permitted_applications.all().values_list('name', flat=True))

    def email_list(self, obj):
        return ', '.join(obj.emails.all().values_list('email', flat=True))
