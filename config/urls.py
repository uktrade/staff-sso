from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin


from sso.oauth2.views import CustomAuthorizationView

from . import api_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^saml2/', include('sso.samlauth.urls')),

    # override the DOT authorisation view
    url(r'^o/authorize/$', CustomAuthorizationView.as_view(), name='authorize'),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^api/v1/', include((api_urls, 'api'), namespace='api-v1')),
]

if getattr(settings, 'LOCAL_AUTH_PAGE'):
    urlpatterns += [
        url(r'^', include('sso.localauth.urls', namespace='localauth'))]
