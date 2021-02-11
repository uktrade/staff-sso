from django.urls import path

from .views import CustomAuthorizationView, CustomIntrospectTokenView

app_name = 'staff_sso_oauth2'

urlpatterns = [
    path('authorize/', CustomAuthorizationView.as_view(), name='authorize'),
    path('introspect/', CustomIntrospectTokenView.as_view(), name='introspect'),
]
