from django.conf import settings
from django.contrib.auth import views
from django.shortcuts import Http404, redirect
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url

from axes.decorators import axes_dispatch

from .models import DomainWhitelist


class FeatureFlaggedMixin:
    def dispatch(self, *args, **kwargs):
        if not getattr(settings, "LOCAL_AUTH_PAGE"):
            raise Http404()
        return super().dispatch(*args, **kwargs)


@method_decorator(axes_dispatch, name="dispatch")
class LoginView(FeatureFlaggedMixin, views.LoginView):
    pass


class LogoutView(views.LogoutView):
    def get_success_url_allowed_hosts(self):
        domains = list(DomainWhitelist.objects.all().values_list("domain", flat=True))
        return {self.request.get_host(), *domains}

    def get_next_page(self):
        next_page = super().get_next_page()

        # the stock get_next_page method redirects to request.path if the url is
        # deemed unsafe.  Instead we want to send the user to
        # settings.LOGOUT_REDIRECT_URL
        if next_page == self.request.path:
            next_page = settings.LOGOUT_REDIRECT_URL

        return next_page
