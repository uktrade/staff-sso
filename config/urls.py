from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView, TemplateView


from sso.healthcheck.views import HealthCheckView
from . import api_urls
from sso.admin.views import admin_login_view
from sso.samlidp.views import LoginProcessView, SSOInitView

app_name = 'staff_sso'

admin.site.site_header = "Staff-SSO Admin Section"
admin.site.site_title = ''
admin.site.index_title = ''

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name=settings.LOGIN_URL)),
    url(r'^admin/login/$', admin_login_view),
    url(r'^admin/', admin.site.urls),
    url(r'^admin/', include('sso.user.admin_urls')),

    # override saml idp login url
    url(r'^idp/login/process/$', LoginProcessView.as_view(), name='saml_login_process_overridden'),
    url(r'^idp/sso/init$', SSOInitView.as_view(), name="saml_idp_init"),

    url(r'^saml2/', include('sso.samlauth.urls')),
    url(r'^idp/', include('djangosaml2idp.urls')),

    # override authorisation and token introspection DOT views
    url(r'^o/', include('sso.oauth2.urls', namespace='oauth2')),
    url(r'^o/', include(('oauth2_provider.urls', 'oauth2_provider'), namespace='oauth2_provider')),

    url(r'^api/v1/', include((api_urls, 'api'), namespace='api-v1')),

    url(r'^', include(('sso.contact.urls', 'sso_contact'), namespace='contact')),
    url(r'^email/', include(('sso.emailauth.urls', 'sso_emailauth'), namespace='emailauth')),
    url(r'^', include(('sso.localauth.urls', 'sso_localauth'), namespace='localauth')),

    url(r'^check/$', HealthCheckView.as_view(), name='healthcheck'),

    url(r'^privacy-policy/$', TemplateView.as_view(template_name='sso/privacy-policy.html'), name='privacy_policy'),
]
