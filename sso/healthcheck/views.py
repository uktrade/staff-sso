import time

from django.views.generic import TemplateView

from sso.user.models import User


class HealthCheckView(TemplateView):
    template_name = 'sso/health-check.html'

    def _do_check(self):
        """Perform a basic DB test"""
        try:
            User.objects.all().count()
            return True
        except Exception:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['status'] = 'OK' if self._do_check() else 'FAIL'

        # nearest approximation of a response time
        context['response_time'] = time.time() - self.request.start_time

        return context

