from django.urls import include, path
from djangosaml2idp import views

from . import views

urlpatterns = [
    path('login/process/', views.LoginProcessView.as_view(), name='saml_login_process_overridden'),
    path('sso/init', views.SSOInitView.as_view(), name="saml_idp_init"),
    path('', include('djangosaml2idp.urls')),
]
