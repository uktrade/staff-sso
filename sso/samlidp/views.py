import logging

from raven.contrib.django.raven_compat.models import client

from djangosaml2idp.views import IdPHandlerViewMixin as IdPHandlerViewMixinBase

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import (HttpResponse, HttpResponseRedirect)
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django.views import View
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect, render
from saml2 import BINDING_HTTP_POST
from saml2.authn_context import PASSWORD, AuthnBroker, authn_context_class_ref
from saml2.ident import NameID
from saml2.s_utils import UnknownPrincipal, UnsupportedBinding

from .forms import SelectEmailForm


logger = logging.getLogger(__name__)


class IdPHandlerViewMixin(IdPHandlerViewMixinBase):
    def render_email_selection_form(self, qs_args):

        user_emails = list(self.request.user.emails.all().values_list('email', flat=True))

        form = SelectEmailForm(email_choices=user_emails)

        return render(self.request, 'djangosaml2idp/select-email.html', {'form': form, 'qs_args': qs_args or []})


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
            client.captureException()
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
            client.captureException()
            return self.handle_error(request, exception=excp, status=400)

        try:
            sp_config = settings.SAML_IDP_SPCONFIG[resp_args['sp_entity_id']]
        except Exception as excp:
            client.captureException()
            return self.handle_error(request, exception=ImproperlyConfigured("No config for SP %s defined in SAML_IDP_SPCONFIG" % resp_args['sp_entity_id']), status=400)

        processor = self.get_processor(resp_args['sp_entity_id'], sp_config)

        # Check if user has access to the service of this SP
        if not processor.has_access(request):
            return self.handle_error(request, exception=PermissionDenied("You do not have access to this resource"), status=403)

        # does the user need to select their email?
        passed_data = request.GET
        if processor.require_email_selection() and request.user.emails.count() > 1:
            selected_email = passed_data.get('email', None)
            if not selected_email or not request.user.emails.filter(email=selected_email).exists():
                return self.render_email_selection_form(passed_data.items())
            else:
                user_id = selected_email
        else:
            user_id = processor.get_user_id(request.user)

        identity = self.get_identity(processor, request.user, sp_config)

        req_authn_context = req_info.message.requested_authn_context or PASSWORD
        AUTHN_BROKER = AuthnBroker()
        AUTHN_BROKER.add(authn_context_class_ref(req_authn_context), "")

        # user_id = processor.get_user_id(request.user)

        # Construct SamlResponse message

        # if the AuthN response does not contain a NameIDPolicy field, we set it to our preferred format
        name_id_policy_format = resp_args['name_id_policy'].format \
            if resp_args['name_id_policy'] else settings.SAML_IDP_CONFIG['service']['idp']['name_id_format'][0]

        try:
            authn_resp = self.IDP.create_authn_response(
                identity=identity, userid=user_id,
                name_id=NameID(format=name_id_policy_format, sp_name_qualifier=resp_args['sp_entity_id'], text=user_id),
                authn=AUTHN_BROKER.get_authn_by_accr(req_authn_context),
                sign_response=self.IDP.config.getattr("sign_response", "idp") or False,
                sign_assertion=self.IDP.config.getattr("sign_assertion", "idp") or False,
                **resp_args)
        except Exception as excp:
            client.captureException()
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


@method_decorator(never_cache, name='dispatch')
class SSOInitView(LoginRequiredMixin, IdPHandlerViewMixin, View):

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        passed_data = request.POST if request.method == 'POST' else request.GET

        # get sp information from the parameters
        try:
            sp_entity_id = passed_data['sp']
        except KeyError as excp:
            return self.handle_error(request, exception=excp, status=400)

        try:
            sp_config = settings.SAML_IDP_SPCONFIG[sp_entity_id]

        except Exception:
            return self.handle_error(request, exception=ImproperlyConfigured("No config for SP %s defined in SAML_IDP_SPCONFIG" % sp_entity_id), status=400)

        # the entity id is overridden for this entry; this solves the issue of all AWS services
        # using the same entity_id, but requiring different configuration
        if 'entity_id' in sp_config:
            sp_entity_id = sp_config['entity_id']

        binding_out, destination = self.IDP.pick_binding(
            service="assertion_consumer_service",
            entity_id=sp_entity_id)

        processor = self.get_processor(sp_entity_id, sp_config)

        # Check if user has access to the service of this SP
        if not processor.has_access(request):
            return self.handle_error(request, exception=PermissionDenied("You do not have access to this resource"), status=403)

        # does the user need to select their email?
        if processor.require_email_selection() and request.user.emails.count() > 1:
            selected_email = passed_data.get('email', None)
            if not selected_email or not request.user.emails.filter(email=selected_email).exists():
                return self.render_email_selection_form(passed_data.items())
            else:
                user_id = selected_email
        else:
            user_id = processor.get_user_id(request.user)

        identity = self.get_identity(processor, request.user, sp_config)

        req_authn_context = PASSWORD
        AUTHN_BROKER = AuthnBroker()
        AUTHN_BROKER.add(authn_context_class_ref(req_authn_context), "")

        # Construct SamlResponse messages
        try:
            name_id_formats = self.IDP.config.getattr("name_id_format", "idp") or [NAMEID_FORMAT_UNSPECIFIED]
            name_id = NameID(format=name_id_formats[0], text=user_id)
            authn = AUTHN_BROKER.get_authn_by_accr(req_authn_context)
            sign_response = self.IDP.config.getattr("sign_response", "idp") or False
            sign_assertion = self.IDP.config.getattr("sign_assertion", "idp") or False
            authn_resp = self.IDP.create_authn_response(
                identity=identity,
                in_response_to="IdP_Initiated_Login",
                destination=destination,
                sp_entity_id=sp_entity_id,
                userid=user_id,
                name_id=name_id,
                authn=authn,
                sign_response=sign_response,
                sign_assertion=sign_assertion,
                **passed_data)
        except Exception as excp:
            return self.handle_error(request, exception=excp, status=500)

        # Return as html with self-submitting form.
        http_args = self.IDP.apply_binding(
            binding=binding_out,
            msg_str="%s" % authn_resp,
            destination=destination,
            relay_state=passed_data['RelayState'],
            response=True)
        return HttpResponse(http_args['data'])


# @method_decorator(login_required, name='dispatch')
# class SelectEmailView(FormView):
#     template_name = 'djangosaml2idp/select-email.html'
#     form_class = SelectEmailForm
#
#     def get_form_kwargs(self):
#
#         kwargs = super().get_form_kwargs()
#
#         kwargs['email_choices'] = list(self.request.user.emails.all().values_list('email', flat=True))
#
#         return kwargs
