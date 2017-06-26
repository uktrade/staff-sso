from django.conf.urls import url

from .views import UserRetrieveViewSet

urlpatterns = [
    url(
        r'^me/$',
        UserRetrieveViewSet.as_view({
            'get': 'retrieve'
        }),
        name='me'
    ),
]
