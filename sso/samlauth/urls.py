from django.conf.urls import url
from djangosaml2 import views as djangosaml2_views

from . import views

urlpatterns = [
    url(r'^login/$', views.login, name='saml2_login'),
    url(r'^acs/$', djangosaml2_views.assertion_consumer_service, name='saml2_acs'),
    url(r'^logout/$', djangosaml2_views.logout, name='saml2_logout'),
    url(r'^ls/post/$', djangosaml2_views.logout_service_post, name='saml2_ls_post'),
    url(r'^metadata/$', djangosaml2_views.metadata, name='saml2_metadata'),
]
