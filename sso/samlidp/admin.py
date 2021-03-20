from django.contrib import admin

#from djangosaml2idp.forms import ServiceProviderAdminForm


class SamlApplicationAdmin(admin.ModelAdmin):
    list_filter = ['active', '_sign_response', '_sign_assertion', '_signing_algorithm', '_digest_algorithm', '_encrypt_saml_responses']
    list_display = ['__str__', 'active', 'description']
    readonly_fields = ('dt_created', 'dt_updated', 'resulting_config',)
    #form = ServiceProviderAdminForm

    fieldsets = (
        ('Identification', {
            'fields': ('entity_id', 'real_entity_id', 'pretty_name', 'description', 'slug', 'start_url')
        }),
        ('Access control', {
            'fields': ('allowed_ips', 'allow_access_by_email_suffix')
        }),
        ('Metadata', {
            'fields': ('metadata_expiration_dt', 'remote_metadata_url', 'local_metadata')
        }),
        ('Configuration', {
            'fields': ('active', '_processor', '_attribute_mapping', '_nameid_field', '_sign_response', '_sign_assertion', '_signing_algorithm', '_digest_algorithm', '_encrypt_saml_responses', 'extra_config'),
        }),
        ('Resulting config', {
            'fields': ('dt_created', 'dt_updated', 'resulting_config')
        })
    )
