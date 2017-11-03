from axes.decorators import watch_login

from django.conf.urls import url
from django.contrib.auth import views as auth_views


urlpatterns = [
    url(r'^login/$', watch_login(auth_views.LoginView.as_view()), name='login'),
    url(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),
]

