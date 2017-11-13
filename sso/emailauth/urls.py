from django.conf.urls import include, url
from django.views.generic import TemplateView

from .views import EmailTokenView, EmailAuthView


urlpatterns = [
    url(r'^token/$', EmailTokenView.as_view(), name='email-auth-initiate'),
    url(r'^signin/(?P<token>[A-Za-z0-9]+)/$', EmailAuthView.as_view(), name='email-auth'),
    url(r'^token/success/$', TemplateView.as_view(template_name='emailauth/complete.html'), name='email-auth-initiate-success'),
    url(r'^invalid-token/$', TemplateView.as_view(template_name='emailauth/invalid-token.html'), name='email-auth-invalid-token')
]
