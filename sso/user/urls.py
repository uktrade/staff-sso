from django.conf.urls import url
from django.urls import path

from .views import UserIntrospectViewSet, UserRetrieveViewSet, UserListViewSet

urlpatterns = [
    path(
        "me/",
        UserRetrieveViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
            }
        ),
        name="me",
    ),
    path("introspect/", UserIntrospectViewSet.as_view({"get": "retrieve"}), name="user-introspect"),
    path("search/", UserListViewSet.as_view({"get": "list"}), name="user-search"),
]
