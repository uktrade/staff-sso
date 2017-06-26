from django.conf.urls import include, url

from sso.user import urls as user_urls

urlpatterns = [
    url(r'^user/', include((user_urls, 'user'), namespace='user')),
]
