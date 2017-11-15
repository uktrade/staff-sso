from django.conf.urls import include, url
from django.views.generic import TemplateView
from .views import EmailTokenView, EmailAuthView, InvalidToken


urlpatterns = [
    url(r'^token/$', EmailTokenView.as_view(), name='email-auth-initiate'),
    url(r'^signin/(?P<token>[A-Za-z0-9]+)/$', EmailAuthView.as_view(), name='email-auth-signin'),
    url(r'^token/success/$', TemplateView.as_view(template_name='emailauth/complete.html'), name='email-auth-initiate-success'),
    url(r'^invalid-token/$', InvalidToken.as_view(), name='email-auth-invalid-token')
]
