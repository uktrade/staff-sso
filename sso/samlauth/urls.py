from django.urls import path
from djangosaml2.views import LogoutInitView, LogoutView, LogoutView, MetadataView

from . import views


urlpatterns = [
    path('login-start/', views.LoginStartView.as_view(), name='saml2_login_start'),
    path('logged-in/', views.logged_in, name='saml2_logged_in'),
    path('logged-out/', views.logged_out, name='saml2_logged_out'),

    path('login/', views.CustomLoginView.as_view(), name='saml2_login'),
    path('acs/', views.CustomAssertionConsumerServiceView.as_view(), name='saml2_acs'),
    
    path('logout/', LogoutInitView.as_view(), name='saml2_logout'),
    path('ls/', LogoutView.as_view(), name='saml2_ls'),
    path('ls/post/', LogoutView.as_view(), name='saml2_ls_post'),
    path('metadata/', MetadataView.as_view(), name='saml2_metadata'),
]
