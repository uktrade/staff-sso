from django.urls import include, path

from sso.core import urls as core_urls
from sso.user import urls as user_urls
from sso.usersettings import urls as user_settings_urls

urlpatterns = [
    path('user/', include((user_urls, 'user'), namespace='user')),
    path('user-settings/', include((user_settings_urls, 'user-settings'), namespace='user-settings')),
    path('', include((core_urls, 'core'), namespace='core')),
]
