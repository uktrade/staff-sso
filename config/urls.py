from django.conf.urls import include, url
from django.contrib import admin

from . import api_urls

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^saml2/', include('sso.samlauth.urls')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^api/v1/', include((api_urls, 'api'), namespace='api-v1')),
]
