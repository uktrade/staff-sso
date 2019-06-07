from django.conf.urls import url

from .views import UserSettingsListView

urlpatterns = [
    url(r'^$',
        UserSettingsListView.as_view(),
        name='list-all-my-settings')
]
