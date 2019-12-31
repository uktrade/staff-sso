import datetime as dt

from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.shortcuts import redirect, render
from django.views.generic import View
from django.views.generic.edit import FormView

from sso.core.logging import create_x_access_log

from .forms import EmailForm
from .models import EmailToken

try:
    from django.urls import reverse, reverse_lazy
except ImportError:
    from django.core.urlresolvers import reverse, reverse_lazy


class InvalidToken(Exception):
    pass


class EmailTokenView(FormView):
    form_class = EmailForm
    template_name = 'emailauth/initiate.html'
    success_url = reverse_lazy('emailauth:email-auth-initiate-success')

    def get(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect('saml2_logged_in')

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):

        form.send_signin_email(self.request)

        response = super().form_valid(form)
        response.set_cookie('sso_auth_email', form.email, expires=dt.datetime.today()+dt.timedelta(days=30))

        return response

    def get_initial(self):

        initial = super().get_initial()

        email = self.request.COOKIES.get('sso_auth_email', None)

        if email:
            username, domain = email.split('@')
            domain = '@' + domain

            if domain in settings.EMAIL_TOKEN_DOMAIN_WHITELIST:
                initial['username'] = username
                initial['domain'] = domain

        return initial


class EmailAuthView(View):
    permanent = False
    query_string = True

    invalid_token_template_name = 'emailauth/invalid-token.html'
    valid_token_template_name = 'emailauth/signin.html'

    def get(self, request, *args, **kwargs):
        try:
            token_obj = self.get_token_object(kwargs['token'])
        except InvalidToken:
            return render(request, self.invalid_token_template_name)

        return render(request, self.valid_token_template_name,
                      {'user': token_obj.get_user().email})

    def post(self, request, *args, **kwargs):
        try:
            token_obj = self.get_token_object(kwargs['token'])
        except InvalidToken:
            return render(request, self.invalid_token_template_name)

        user = token_obj.get_user()
        user.backend = 'django.contrib.auth.backends.ModelBackend'

        login(self.request, user)

        token_obj.mark_used()

        create_x_access_log(request, 200, message='Email Token Auth', email=token_obj.email)
        get_user_model().objects.set_email_last_login_time(token_obj.email)

        return redirect(self.get_next_url())

    def get_token_object(self, token):
        try:
            token_obj = EmailToken.objects.get(token=token, used=False)
        except EmailToken.DoesNotExist:
            raise InvalidToken

        if token_obj.is_expired:
            raise InvalidToken

        return token_obj

    def get_next_url(self):
        next_url = self.request.GET.get('next', '').strip()

        if next_url:
            return next_url
        else:
            return reverse('saml2_logged_in')
