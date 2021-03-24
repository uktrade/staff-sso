from django.conf.urls import url
from django.urls import path, re_path
from django.views.generic import TemplateView

from .views import EmailAuthView, EmailTokenView

app_name = "emailauth"

urlpatterns = [
    path("token/", EmailTokenView.as_view(), name="email-auth-initiate"),
    re_path(
        r"^signin/(?P<token>[A-Za-z0-9]+)/$", EmailAuthView.as_view(), name="email-auth-signin"
    ),
    path(
        "token/success/",
        TemplateView.as_view(template_name="emailauth/complete.html"),
        name="email-auth-initiate-success",
    ),
]
