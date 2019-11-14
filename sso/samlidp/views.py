import logging

from django.shortcuts import redirect

from djangosaml2idp.error_views import SamlIDPErrorView
from djangosaml2idp.views import IdPHandlerViewMixin

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import (HttpResponse, HttpResponseRedirect)
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from saml2 import BINDING_HTTP_POST
from saml2.authn_context import PASSWORD, AuthnBroker, authn_context_class_ref
from saml2.ident import NameID
from saml2.s_utils import UnknownPrincipal, UnsupportedBinding


logger = logging.getLogger(__name__)


class CustomSamlIDPErrorView(SamlIDPErrorView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if context and 'PermissionDenied' in context['exception_type']:
            return redirect('contact:access-denied')
        return self.render_to_response(context)



@method_decorator(never_cache, name='dispatch')
class LoginProcessView(LoginRequiredMixin, IdPHandlerViewMixin, View):
    """ View which processes the actual SAML request and returns a self-submitting form with the SAML response.
        The login_required decorator ensures the user authenticates first on the IdP using 'normal' ways.

        NOTE: this view has been overridden from djangosamlidp package due to a bug in the way saml redirect signature
        checking is being handled.  This appears to be fixed in an PR for this app.  Once that PR has been merged,
        this function and tne associated url entry can be removed.
    """

    def get(self, request, *args, **kwargs):
        binding = request.session.get('Binding', BINDING_HTTP_POST)

        # Parse incoming request
        try:
            req_info = self.IDP.parse_authn_request(request.session['SAMLRequest'], binding)
        except Exception as excp:
            return self.handle_error(request, exception=excp)

        # Signature verification
        # for authn request signature_check is saml2.sigver.SecurityContext.correctly_signed_authn_request
        verified_ok = req_info.signature_check(req_info.xmlstr)
        if not verified_ok:
            return self.handle_error(request,
                                     extra_message="Message signature verification failure",
                                     status=400)

        # Gather response arguments
        try:
            resp_args = self.IDP.response_args(req_info.message)
        except (UnknownPrincipal, UnsupportedBinding) as excp:
            return self.handle_error(request, exception=excp, status=400)

        try:
            sp_config = settings.SAML_IDP_SPCONFIG[resp_args['sp_entity_id']]
        except Exception:
            return self.handle_error(request, exception=ImproperlyConfigured("No config for SP %s defined in SAML_IDP_SPCONFIG" % resp_args['sp_entity_id']), status=400)

        processor = self.get_processor(resp_args['sp_entity_id'], sp_config)

        # Check if user has access to the service of this SP
        if not processor.has_access(request):
            return self.handle_error(request, exception=PermissionDenied("You do not have access to this resource"), status=403)

        identity = self.get_identity(processor, request.user, sp_config)

        req_authn_context = req_info.message.requested_authn_context or PASSWORD
        AUTHN_BROKER = AuthnBroker()
        AUTHN_BROKER.add(authn_context_class_ref(req_authn_context), "")

        user_id = processor.get_user_id(request.user)

        # Construct SamlResponse message
        try:
            authn_resp = self.IDP.create_authn_response(
                identity=identity, userid=user_id,
                name_id=NameID(format=resp_args['name_id_policy'].format, sp_name_qualifier=resp_args['sp_entity_id'], text=user_id),
                authn=AUTHN_BROKER.get_authn_by_accr(req_authn_context),
                sign_response=self.IDP.config.getattr("sign_response", "idp") or False,
                sign_assertion=self.IDP.config.getattr("sign_assertion", "idp") or False,
                **resp_args)
        except Exception as excp:
            return self.handle_error(request, exception=excp, status=500)

        http_args = self.IDP.apply_binding(
            binding=resp_args['binding'],
            msg_str="%s" % authn_resp,
            destination=resp_args['destination'],
            relay_state=request.session['RelayState'],
            response=True)

        logger.debug('http args are: %s' % http_args)

        return self.render_response(request, processor, http_args)

    def render_response(self, request, processor, http_args):
        """ Return either as redirect to MultiFactorView or as html with self-submitting form.
        """
        if processor.enable_multifactor(request.user):
            # Store http_args in session for after multi factor is complete
            request.session['saml_data'] = http_args['data']
            logger.debug("Redirecting to process_multi_factor")
            return HttpResponseRedirect(reverse('saml_multi_factor'))
        logger.debug("Performing SAML redirect")
        return HttpResponse(http_args['data'])
