from django.conf.urls import url

from .views import UserRetrieveViewSet, UserIntrospectViewSet

urlpatterns = [
    url(
        r'^me/$',
        UserRetrieveViewSet.as_view({
            'get': 'retrieve'
        }),
        name='me'
    ),
    url(
        r'^introspect/$',
        UserIntrospectViewSet.as_view({
            'get': 'retrieve'
        }),
        name='user-introspect'
    ),
]
