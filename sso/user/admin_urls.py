from django.urls import path, re_path

from .admin_views import (
    EmailLastLoginExportView,
    ShowUserPermissionsView,
    UserDataExportView,
)

urlpatterns = [
    path("user/export-list/", UserDataExportView.as_view(), name="user-export-view"),
    path("user/export-email-list/", EmailLastLoginExportView.as_view(), name="email-export-view"),
    re_path(
        r"^user/show-permissions/(?P<user_id>\d+)/$",
        ShowUserPermissionsView.as_view(),
        name="show-permissions-view",
    ),
]
