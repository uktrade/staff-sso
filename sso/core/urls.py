from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^activity-stream/$', views.activity_stream, name='activity-stream'),
]
