from django.urls import path
from django.urls import path

from .views import UserSettingsListView

urlpatterns = [
    path('',
        UserSettingsListView.as_view(),
        name='list-all-my-settings')
]
