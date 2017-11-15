from django.conf import settings
from django.contrib.auth import views
from django.shortcuts import Http404


class FeatureFlaggedMixin:
    def dispatch(self, *args, **kwargs):
        if not getattr(settings, 'LOCAL_AUTH_PAGE'):
            raise Http404()
        return super().dispatch(*args, **kwargs)



class LoginView(FeatureFlaggedMixin, views.LoginView):
    pass


class LogoutView(FeatureFlaggedMixin, views.LogoutView):
    pass
