from django.conf.urls import url

from .views import CustomAuthorizationView, CustomIntrospectTokenView

app_name = 'staff_sso_oauth2'

urlpatterns = [
    url(r'^authorize/$', CustomAuthorizationView.as_view(), name='authorize'),
    url(r'^introspect/$', CustomIntrospectTokenView.as_view(), name='introspect'),
]
