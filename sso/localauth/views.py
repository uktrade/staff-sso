from django.conf import settings
from django.contrib.auth import views
from django.shortcuts import Http404, redirect


class FeatureFlaggedMixin:
    def dispatch(self, *args, **kwargs):
        if not getattr(settings, 'LOCAL_AUTH_PAGE'):
            raise Http404()
        return super().dispatch(*args, **kwargs)


class LoginView(FeatureFlaggedMixin, views.LoginView):
    pass


def session_logout(request):
    """
    Basic logout that destroys session to logout the user and remove any saml2
    remnants.
    """
    request.session.flush()

    came_from = request.GET.get('next', settings.LOGOUT_REDIRECT_URL)
    if not came_from:
        came_from = settings.LOGIN_REDIRECT_URL

    return redirect(came_from)
