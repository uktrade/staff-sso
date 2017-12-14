from django.conf.urls import url

from .admin_views import (
    AdminUserAliasAddImportView, AdminUserMergeImportView, download_user_csv
)

urlpatterns = [
    url(r'^user-import/$', AdminUserMergeImportView.as_view(), name='admin-user-merge-import'),
    url(r'^user-alias-import/$', AdminUserAliasAddImportView.as_view(), name='admin-user-alias-import'),
    url(r'^user/csv-download/$', download_user_csv, name='user-csv-download'),
]
