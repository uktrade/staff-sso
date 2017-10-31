from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('email', )
    fields = ('email', 'is_superuser', 'date_joined', 'last_login', 'permitted_applications')
    readonly_fields = ('email', 'password', 'date_joined', 'last_login')
    list_display = ('email', 'is_superuser', 'last_login', 'permitted_apps')

    def permitted_apps(self, obj):
        return ', '.join(f.name for f in obj.permitted_applications.all())

    def has_add_permission(self, request):
        return False
