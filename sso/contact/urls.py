from django.conf.urls import url
from django.views.generic import TemplateView

from .views import AccessDeniedView


urlpatterns = [
    url(r'^access-denied/$', AccessDeniedView.as_view()),
    url(r'^access-denied/success/$', TemplateView.as_view(template_name='sso/success.html'), name='success'),
]
