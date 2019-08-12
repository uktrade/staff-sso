from django.conf.urls import url

from .views import (
    UserIntrospectViewSet,
    UserRetrieveViewSet,
    UserListViewSet
)

urlpatterns = [
    url(
        r'^me/$',
        UserRetrieveViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
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
    url(
        r'^search/$',
        UserListViewSet.as_view({
            'get': 'list'
        }),
        name='user-search'
    ),
]
