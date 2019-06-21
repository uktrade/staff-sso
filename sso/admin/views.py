from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied


def admin_login_view(request):
    """A replacement admin login view that will direct the user through the SSO
    authentication flow. """

    next_url = request.GET.get(
        'next',
        reverse('admin:index')
    )

    if request.user.is_authenticated:
        if not request.user.is_staff:
            raise PermissionDenied

        return redirect(next_url)

    return redirect('%s?next=%s' % (reverse('saml2_login'), next_url))
