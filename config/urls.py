from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView

from sso.healthcheck.views import HealthCheckView
from sso.user.admin_views import download_user_csv

from . import api_urls
from sso.user.admin_views import AdminUserImportView
from . import api_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin/user/csv-download/$', download_user_csv, name='user-csv-download'),
    url(r'^saml2/', include('sso.samlauth.urls')),

    # override authorisation and token introspection DOT views
    url(r'^o/', include('sso.oauth2.urls', namespace='oauth2')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^api/v1/', include((api_urls, 'api'), namespace='api-v1')),

    url(r'^access-denied/$', TemplateView.as_view(template_name='sso/access-denied.html'), name='access-denied'),
    url(r'^email/', include('sso.emailauth.urls')),
    url(r'^', include('sso.localauth.urls', namespace='localauth')),
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^admin/user-import/$', AdminUserImportView.as_view(), name='admin-user-import'),
    url(r'^admin/', admin.site.urls),

    url(r'^check/$', HealthCheckView.as_view(), name='healthcheck'),
]
