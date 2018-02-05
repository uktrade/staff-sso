from django.conf.urls import url

from .admin_views import (
    AdminUserAliasAddImportView, AdminUserMergeImportView, UserDataExportView, UserPermissionExportView
)

urlpatterns = [
    url(r'^user-import/$', AdminUserMergeImportView.as_view(), name='admin-user-merge-import'),
    url(r'^user-alias-import/$', AdminUserAliasAddImportView.as_view(), name='admin-user-alias-import'),
    url(r'^user/export-list/$', UserDataExportView.as_view(), name='user-export-view'),
    url(r'^user/export-permissions-list/$', UserPermissionExportView.as_view(), name='user-permission-export-view'),
]