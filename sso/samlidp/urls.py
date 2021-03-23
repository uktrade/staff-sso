from django.urls import include, path
from djangosaml2idp import views

app_name = 'samlidp'

urlpatterns = [
    # The url patterns changed in the latest version of djangosamlidp to add trailing slashes.
    # These paths are added to maintain backwards compatability and can be removed when each
    # SP has been updated with the latest IdP metadata.
    path('sso/init', views.SSOInitView.as_view(), name="saml_idp_init_legacy"),
    path('sso/<str:binding>', views.sso_entry, name="saml_login_binding_legacy"),
]
