import time

from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from raven.contrib.django.raven_compat.models import client


class HealthCheckView(TemplateView):
    template_name = 'sso/health-check.html'

    def _do_check(self):
        """Perform a basic DB test"""
        try:
            get_user_model().objects.exists()
            return True

        except Exception:
            client.captureException()
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['status'] = 'OK' if self._do_check() else 'FAIL'

        # nearest approximation of a response time
        context['response_time'] = time.time() - self.request.start_time

        return context
