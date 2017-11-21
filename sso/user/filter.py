from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from sso.oauth2.models import Application


class ApplicationFilter(admin.SimpleListFilter):

    title = _('application')

    parameter_name = 'application'

    def lookups(self, request, model_admin):

        options = list(Application.objects.values_list('id', 'name'))
        options.append(
            ('noperms', 'Users with no permissions')
        )

        return options

    def queryset(self, request, queryset):
        if self.value():
            query = None if self.value() == 'noperms' else self.value()
            return queryset.filter(permitted_applications=query)
