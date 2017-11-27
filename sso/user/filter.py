from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from sso.oauth2.models import Application


class ApplicationFilter(admin.SimpleListFilter):

    title = _('application')

    parameter_name = 'application'

    def lookups(self, request, model_admin):

        return Application.objects.values_list('id', 'name')

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(permitted_applications__id=self.value())
