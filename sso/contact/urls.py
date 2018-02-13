from django.conf.urls import url

from .views import AccessDeniedView


urlpatterns = [
    url(r'^access-denied/$', AccessDeniedView.as_view(), name='access-denied'),
]
