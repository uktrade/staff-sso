from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse_lazy

from .forms import RequestAccessForm


class AccessDeniedView(FormView):
    template_name = 'sso/access-denied.html'
    form_class = RequestAccessForm
    success_url = reverse_lazy('contact:success')

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = {}

        if self.request.user.is_authenticated:
            email = self.request.user.email
        else:
            email = 'Unspecified'

        initial['email'] = email
        initial['application'] = self.request.session.pop('_last_failed_access_app', 'Unspecified')

        return initial

    def form_valid(self, form):

        form.create_zendesk_ticket()
        return super().form_valid(form)
