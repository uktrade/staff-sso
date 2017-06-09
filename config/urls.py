from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^saml2/', include('sso.samlauth.urls')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
