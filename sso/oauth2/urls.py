from django.conf.urls import include, url

from .views import CustomAuthorizationView, CustomIntrospectTokenView

urlpatterns = [
    url(r'^authorize/$', CustomAuthorizationView.as_view(), name='authorize'),
    url(r"^introspect/$", CustomIntrospectTokenView.as_view(), name="introspect"),
]

