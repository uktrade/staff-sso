from django.shortcuts import redirect
from django.views.generic.edit import FormView
from django.views.generic.base import RedirectView, TemplateView
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

        form.send_email(self.request)

        return super().form_valid(form)


class EmailAuthView(TemplateView):
    permanent = False
    query_string = True

    template_name = 'emailauth/initiate.html'

    def get(self, request, *args, **kwargs):
    #def get_redirect_url(self, *args, **kwargs):
        try:
            token_obj = EmailToken.objects.get(token=kwargs['token'], used=False)
        except EmailToken.DoesNotExist:
            return reverse('email-auth-invalid-token')

        if token_obj.is_expired:
            return reverse('email-auth-invalid-token')

        user = token_obj.get_user()
        user.backend = 'sso.emailauth.backends.PasswordlessAuthBackend'

        login(self.request, user)

        next_url = self.request.GET.get('next')
        token_obj.mark_used()

        return super().get(request, *args, **kwargs)

        if next_url not in ['None', None]:
            return next_url
        else:
            return reverse('saml2_logged_in')
