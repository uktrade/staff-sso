from django.shortcuts import redirect

from djangosaml2idp.error_views import SamlIDPErrorView


class CustomSamlIDPErrorView(SamlIDPErrorView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if context and "PermissionDenied" in context["exception_type"]:
            return redirect("contact:access-denied")
        return self.render_to_response(context)
