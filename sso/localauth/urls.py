from axes.decorators import axes_dispatch
from django.conf.urls import url

from sso.localauth import views

urlpatterns = [
    url(r'^login/$', axes_dispatch(views.LoginView.as_view()), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='session-logout'),
]
