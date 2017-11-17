from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView

from sso.healthcheck.views import HealthCheckView
from sso.oauth2.views import CustomAuthorizationView
from . import api_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^saml2/', include('sso.samlauth.urls')),

    # override the DOT authorisation view
    url(r'^o/authorize/$', CustomAuthorizationView.as_view(), name='authorize'),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^api/v1/', include((api_urls, 'api'), namespace='api-v1')),

    url(r'^access-denied/$', TemplateView.as_view(template_name='sso/access-denied.html'), name='access-denied'),
    url(r'^email/', include('sso.emailauth.urls')),
    url(r'^', include('sso.localauth.urls', namespace='localauth')),

    url(r'^check/$', HealthCheckView.as_view(), name='healthcheck')
]
