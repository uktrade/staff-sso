from django.conf.urls import include, url

from sso.user import urls as user_urls
from sso.usersettings import urls as user_settings_urls

urlpatterns = [
    url(r'^user/', include((user_urls, 'user'), namespace='user')),
    url(r'^user-settings/', include((user_settings_urls, 'user-settings'), namespace='user-settings')),
]
