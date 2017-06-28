from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('email', )
    fields = ('email', 'password', 'groups', 'is_superuser', 'date_joined', 'last_login')
    readonly_fields = ('email', 'password', 'date_joined', 'last_login')
    list_display = ('email', 'is_superuser', 'last_login')

    def has_add_permission(self, request):
        return False
