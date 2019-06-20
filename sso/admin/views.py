from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied


NEXT_URL_SESSION_KEY = '_admin_next_url'


def admin_login_view(request):
    """A replacement admin login view that will direct the user through the SSO
    authentication flow. """

    next_url = request.GET.get(
        'next',
        request.session.get(NEXT_URL_SESSION_KEY,
                            reverse('admin:index')))

    if request.user.is_authenticated:
        if not request.user.is_staff:
            raise PermissionDenied
        else:
            if NEXT_URL_SESSION_KEY in request.session:
                del request.session[NEXT_URL_SESSION_KEY]

            return redirect(next_url)
    else:
        request.session[NEXT_URL_SESSION_KEY] = next_url

        return redirect('%s?next=%s' % (reverse('saml2_login'), next_url))
