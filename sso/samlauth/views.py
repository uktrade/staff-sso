import datetime as dt
import logging
from urllib.parse import parse_qs, quote, quote_plus, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import is_safe_url
from django.views.generic.edit import FormView

from djangosaml2.conf import get_config
from djangosaml2.utils import available_idps
from djangosaml2.views import AssertionConsumerServiceView
from sso.core.logging import create_x_access_log
from sso.emailauth.models import EmailToken

from .forms import EmailForm

logger = logging.getLogger('sso.samlauth')


SSO_EMAIL_SESSION_KEY = 'sso_auth_email'


class CustomAssertionConsumerServiceView(AssertionConsumerServiceView):

    def post_login_hook(
        self, request: HttpRequest, user: settings.AUTH_USER_MODEL, session_info: dict
    ) -> None:

        email = session_info['ava']['email'][0]

        # log the successful authentication
        create_x_access_log(
            request,
            200,
            message='Remote IdP Auth',
            entity_id=session_info['issuer'],
            email=email,
        )

        # record the last login time against the specific email.
        get_user_model().objects.set_email_last_login_time(email)


@login_required
def logged_in(request):
    """
    Fallback view after logging in if no redirect url is specified.
    """

    return render(
        request,
        'sso/logged-in.html',
        {
            'oauth2_applications': request.user.get_permitted_applications(),
        },
    )


def logged_out(request):
    """
    Fallback view after logging out if no redirect url is specified.
    """
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('saml2_logged_in'))
    return render(request, 'sso/logged-out.html')


class LoginStartView(FormView):
    form_class = EmailForm
    template_name = 'sso/login-initiate.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('saml2_logged_in')

        return super().dispatch(request, *args, **kwargs)

    def get_next_url(self):
        """extract the next url from the querystring, if present"""

        if 'next' in self.request.GET:
            next_url = self.request.GET['next']

            if is_safe_url(url=next_url, allowed_hosts=settings.ALLOWED_HOSTS):
                return next_url

        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['next'] = self.get_next_url()

        return context

    def get_initial(self):

        initial = super().get_initial()

        email = self.request.COOKIES.get(SSO_EMAIL_SESSION_KEY, None)

        if email:
            initial['email'] = email

        return initial

    def lookup_idp_from_ref(self, ref):

        conf = get_config(None, self.request)
        idps = available_idps(conf)

        return [k for k, v in idps.items() if v == ref][0]

    def form_valid(self, form):

        email = form.cleaned_data['email']

        if form.idp_ref:
            idp = quote(self.lookup_idp_from_ref(form.idp_ref))
            url = reverse('saml2_login') + f'?idp={idp}'
            args = self.request.META.get('QUERY_STRING', '')

            if args:
                url = '%s&%s' % (url, args)

            response = redirect(url)
        else:
            self.send_signin_email(form.cleaned_data['email'])

            response = redirect('emailauth:email-auth-initiate-success')

        response.set_cookie(
            SSO_EMAIL_SESSION_KEY,
            email,
            expires=dt.datetime.today() + dt.timedelta(days=30),
        )

        return response

    def extract_redirect_url(self, next_url):
        """Attempt to extract the domain of the redirect_uri querystring param
        in the next url, e.g:

        ?next=/o/authorize/%3Fredirect_uri%3Dhttps%253A%252F%252Fworkspace ...
        """
        oauth2_url = urlparse(next_url)

        qs_items = parse_qs(oauth2_url.query)

        try:
            redirect_url = qs_items['redirect_uri'][0]
        except KeyError:
            return next_url

        url = urlparse(redirect_url)
        redirect_url = f'{url.scheme}://{url.netloc}'

        return redirect_url

    def send_signin_email(self, email):
        """
        Generate an EmailToken and send a sign in email to the user
        """
        token = EmailToken.objects.create_token(email)
        next_url = self.get_next_url()

        if next_url:
            next_url = quote_plus(self.extract_redirect_url(next_url))

        path = reverse('emailauth:email-auth-signin', kwargs=dict(token=token))

        url = '{scheme}{host}{path}?next={next_url}'.format(
            scheme='https://',
            host=self.request.get_host(),
            path=path,
            next_url=next_url,
        )

        subject = render_to_string('emailauth/email_subject.txt').strip()
        message = render_to_string('emailauth/email.txt', context=dict(auth_url=url))

        send_mail(
            subject,
            message,
            settings.EMAIL_FROM,
            [email],
            fail_silently=False,
        )
