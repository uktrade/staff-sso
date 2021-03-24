from django.urls import path

from .views import AccessDeniedView


urlpatterns = [
    path("access-denied/", AccessDeniedView.as_view(), name="access-denied"),
]
