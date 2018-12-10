from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.generic import View
from django.views.generic.edit import FormView

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

        return super().form_valid(form)


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
        next_url = self.request.GET.get('next')

        if next_url not in ['None', None]:
            return next_url
        else:
            return reverse('saml2_logged_in')
