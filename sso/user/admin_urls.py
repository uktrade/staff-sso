from django.conf.urls import url

from .admin_views import (
    ShowUserPermissionsView,
    UserDataExportView,
)

urlpatterns = [
    url(r'^user/export-list/$', UserDataExportView.as_view(), name='user-export-view'),
    url(r'^user/show-permissions/(?P<user_id>\d+)/$', ShowUserPermissionsView.as_view(), name='show-permissions-view'),
]
