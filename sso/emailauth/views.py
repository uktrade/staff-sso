from urllib.parse import quote_plus

from django.shortcuts import redirect
from django.views.generic.edit import FormView
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.auth import login

from .forms import EmailForm
from .models import EmailToken


class EmailTokenView(FormView):
    form_class = EmailForm
    template_name = 'emailauth/initiate.html'
    success_url = reverse_lazy('email-auth-initiate-success')

    def get(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect('saml2_logged_in')

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):

        form.send_signin_email(self.request)

        return super().form_valid(form)


class EmailAuthView(RedirectView):
    permanent = False
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        next_url = self.request.GET.get('next')

        invalid_token_url = reverse('email-auth-invalid-token')

        if next_url:
            invalid_token_url = "{url}?next={qs}".format(
                url = invalid_token_url,
                qs = quote_plus(next_url)
            )

        try:
            token_obj = EmailToken.objects.get(token=kwargs['token'], used=False)
        except EmailToken.DoesNotExist:
            return invalid_token_url

        if token_obj.is_expired:
            return invalid_token_url

        user = token_obj.get_user()
        user.backend = 'django.contrib.auth.backends.ModelBackend'

        login(self.request, user)

        token_obj.mark_used()

        if next_url not in ['None', None]:
            return next_url
        else:
            return reverse('saml2_logged_in')


class InvalidToken(TemplateView):
    template_name = 'emailauth/invalid-token.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['next_url'] = self.request.GET.get('next', '')

        return context

