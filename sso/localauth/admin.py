from django.contrib import admin

from .models import DomainWhitelist


@admin.register(DomainWhitelist)
class DomainWhitelistAdmin(admin.ModelAdmin):
    list_display = ("domain",)
