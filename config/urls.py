from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from django.views.generic.base import RedirectView, TemplateView

from sso.admin.views import admin_login_view
from sso.healthcheck.views import HealthCheckView
from . import api_urls

app_name = "staff_sso"

admin.site.site_header = "Staff-SSO Admin Section"
admin.site.site_title = ""
admin.site.index_title = ""

urlpatterns = [
    path("", RedirectView.as_view(pattern_name=settings.LOGIN_URL)),
    path("admin/login/", admin_login_view),
    path("admin/", admin.site.urls),
    path("admin/", include("sso.user.admin_urls")),
    path("saml2/", include("sso.samlauth.urls")),
    path("idp/", include("djangosaml2idp.urls", namespace="djangosaml2idp")),
    path("idp/", include("sso.samlidp.urls", namespace="samlidp")),
    # override authorisation and token introspection DOT views
    path("o/", include("sso.oauth2.urls", namespace="oauth2")),
    path("o/", include(("oauth2_provider.urls", "oauth2_provider"), namespace="oauth2_provider")),
    path("api/v1/", include((api_urls, "api"), namespace="api-v1")),
    path("", include(("sso.contact.urls", "sso_contact"), namespace="contact")),
    path("email/", include(("sso.emailauth.urls", "sso_emailauth"), namespace="emailauth")),
    path("", include(("sso.localauth.urls", "sso_localauth"), namespace="localauth")),
    path("check/", HealthCheckView.as_view(), name="healthcheck"),
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="sso/privacy-policy.html"),
        name="privacy_policy",
    ),
]
