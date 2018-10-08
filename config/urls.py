from django.conf.urls import include, url
from django.contrib import admin

from sso.healthcheck.views import HealthCheckView
from . import api_urls

app_name = 'staff_sso'

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^admin/', include('sso.user.admin_urls')),

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
]
