from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    path('activity-stream/', views.activity_stream, name='activity-stream'),
]
