from axes.decorators import watch_login

from django.conf.urls import url
from sso.localauth import views


urlpatterns = [
    url(r'^login/$', watch_login(views.LoginView.as_view()), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
]
