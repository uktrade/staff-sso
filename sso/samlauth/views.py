import base64
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseRedirect,
    HttpResponseServerError
)
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import is_safe_url
from django.utils.six import text_type
from djangosaml2.cache import IdentityCache, OutstandingQueriesCache, StateCache
from djangosaml2.conf import get_config
from djangosaml2.utils import (
    available_idps, get_idp_sso_supported_bindings, get_location
)
from djangosaml2.views import _get_subject_id, finish_logout
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.s_utils import UnsupportedBinding
from saml2.xmldsig import SIG_RSA_SHA256

logger = logging.getLogger('sso.samlauth')


def login(request,  # noqa: C901
          config_loader_path=None,
          wayf_template='djangosaml2/wayf.html',
          authorization_error_template='djangosaml2/auth_error.html',
          post_binding_form_template='djangosaml2/post_binding_form.html'):
    """SAML Authorization Request initiator

    This view initiates the SAML2 Authorization handshake
    using the pysaml2 library to create the AuthnRequest.
    It uses the SAML 2.0 Http Redirect protocol binding.

    * post_binding_form_template - path to a template containing HTML form with
    hidden input elements, used to send the SAML message data when HTTP POST
    binding is being used. You can customize this template to include custom
    branding and/or text explaining the automatic redirection process. Please
    see the example template in
    templates/djangosaml2/example_post_binding_form.html
    If set to None or nonexistent template, default form from the saml2 library
    will be rendered.
    """

    logger.debug('Login process started')

    came_from = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
    if not came_from:
        logger.warning('The next parameter exists but is empty')
        came_from = settings.LOGIN_REDIRECT_URL

    # Ensure the user-originating redirection url is safe.
    if not is_safe_url(url=came_from, host=request.get_host()):
        came_from = settings.LOGIN_REDIRECT_URL

    # if the user is already authenticated that maybe because of two reasons:
    # A) He has this URL in two browser windows and in the other one he
    #    has already initiated the authenticated session.
    # B) He comes from a view that (incorrectly) send him here because
    #    he does not have enough permissions. That view should have shown
    #    an authorization error in the first place.
    # We can only make one thing here and that is configurable with the
    # SAML_IGNORE_AUTHENTICATED_USERS_ON_LOGIN setting. If that setting
    # is True (default value) we will redirect him to the came_from view.
    # Otherwise, we will show an (configurable) authorization error.
    if not request.user.is_anonymous():
        try:
            redirect_authenticated_user = settings.SAML_IGNORE_AUTHENTICATED_USERS_ON_LOGIN
        except AttributeError:
            redirect_authenticated_user = True

        if redirect_authenticated_user:
            return HttpResponseRedirect(came_from)
        else:
            logger.debug('User is already logged in')
            return render(
                request, authorization_error_template, {
                    'came_from': came_from,
                }
            )

    selected_idp = request.GET.get('idp', None)
    conf = get_config(config_loader_path, request)

    # is a embedded wayf needed?
    idps = available_idps(conf)
    if selected_idp is None and len(idps) > 1:
        logger.debug('A discovery process is needed')

        idps = sorted(idps.items(), key=lambda x: x[1])
        return render(
            request, wayf_template, {
                'available_idps': idps,
                'came_from': came_from,
            }
        )

    # choose a binding to try first
    sign_requests = getattr(conf, '_sp_authn_requests_signed', False)
    binding = BINDING_HTTP_POST if sign_requests else BINDING_HTTP_REDIRECT
    logger.debug('Trying binding %s for IDP %s', binding, selected_idp)

    # ensure our selected binding is supported by the IDP
    supported_bindings = get_idp_sso_supported_bindings(selected_idp, config=conf)
    if binding not in supported_bindings:
        logger.debug('Binding %s not in IDP %s supported bindings: %s',
                     binding, selected_idp, supported_bindings)
        if binding == BINDING_HTTP_POST:
            logger.warning('IDP %s does not support %s,  trying %s',
                           selected_idp, binding, BINDING_HTTP_REDIRECT)
            binding = BINDING_HTTP_REDIRECT
        else:
            logger.warning('IDP %s does not support %s,  trying %s',
                           selected_idp, binding, BINDING_HTTP_POST)
            binding = BINDING_HTTP_POST
        # if switched binding still not supported, give up
        if binding not in supported_bindings:
            raise UnsupportedBinding('IDP %s does not support %s or %s',
                                     selected_idp, BINDING_HTTP_POST, BINDING_HTTP_REDIRECT)

    client = Saml2Client(conf)
    http_response = None

    logger.debug('Redirecting user to the IdP via %s binding.', binding)
    if binding == BINDING_HTTP_REDIRECT:
        try:
            # do not sign the xml itself, instead us the sigalg to
            # generate the signature as a URL param
            sigalg = SIG_RSA_SHA256 if sign_requests else None
            session_id, result = client.prepare_for_authenticate(
                entityid=selected_idp, relay_state=came_from,
                binding=binding, sign=False, sigalg=sigalg)
        except TypeError as e:
            logger.error('Unable to know which IdP to use')
            return HttpResponse(text_type(e))
        else:
            http_response = HttpResponseRedirect(get_location(result))
    elif binding == BINDING_HTTP_POST:
        # use the html provided by pysaml2 if no template specified
        if not post_binding_form_template:
            try:
                session_id, result = client.prepare_for_authenticate(
                    entityid=selected_idp, relay_state=came_from,
                    binding=binding,
                    sign_alg=SIG_RSA_SHA256)
            except TypeError as e:
                logger.error('Unable to know which IdP to use')
                return HttpResponse(text_type(e))
            else:
                http_response = HttpResponse(result['data'])
        # get request XML to build our own html based on the template
        else:
            try:
                location = client.sso_location(selected_idp, binding)
            except TypeError as e:
                logger.error('Unable to know which IdP to use')
                return HttpResponse(text_type(e))
            session_id, request_xml = client.create_authn_request(
                location,
                binding=binding,
                sign_alg=SIG_RSA_SHA256)
            http_response = render(request, post_binding_form_template, {
                'target_url': location,
                'params': {
                    'SAMLRequest': base64.b64encode(force_bytes(request_xml)),
                    'RelayState': came_from,
                },
            })
    else:
        raise UnsupportedBinding('Unsupported binding: %s', binding)

    # success, so save the session ID and return our response
    logger.debug('Saving the session_id in the OutstandingQueries cache')
    oq_cache = OutstandingQueriesCache(request.session)
    oq_cache.set(session_id, came_from)
    return http_response


@login_required
def logged_in(request):
    """
    Fallback view after logging in if no redirect url is specified.
    """
    return render(request, 'sso/logged-in.html')


@login_required
def logout(request, config_loader_path=None):
    """SAML Logout Request initiator

    This view initiates the SAML2 Logout request
    using the pysaml2 library to create the LogoutRequest.
    """
    logger.debug('Logout process started')
    state = StateCache(request.session)
    conf = get_config(config_loader_path, request)

    client = Saml2Client(conf, state_cache=state,
                         identity_cache=IdentityCache(request.session))
    subject_id = _get_subject_id(request.session)
    if subject_id is None:
        logger.warning(
            'The session does not contains the subject id for user %s',
            request.user)

    result = client.global_logout(subject_id, sign=True, sign_alg=SIG_RSA_SHA256)

    state.sync()

    if not result:
        logger.error('Looks like the user %s is not logged in any IdP/AA', subject_id)
        return HttpResponseBadRequest('You are not logged in any IdP/AA')

    if len(result) > 1:
        logger.error('Sorry, I do not know how to logout from several sources. I will logout just from the first one')

    for entityid, logout_info in result.items():
        if isinstance(logout_info, tuple):
            binding, http_info = logout_info
            if binding == BINDING_HTTP_POST:
                logger.debug('Returning form to the IdP to continue the logout process')
                body = ''.join(http_info['data'])
                return HttpResponse(body)
            elif binding == BINDING_HTTP_REDIRECT:
                logger.debug('Redirecting to the IdP to continue the logout process')
                return HttpResponseRedirect(get_location(http_info))
            else:
                logger.error('Unknown binding: %s', binding)
                return HttpResponseServerError('Failed to log out')
        else:
            # We must have had a soap logout
            return finish_logout(request, logout_info)

    logger.error('Could not logout because there only the HTTP_REDIRECT is supported')
    return HttpResponseServerError('Logout Binding not supported')


def logged_out(request):
    """
    Fallback view after logging out if no redirect url is specified.
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('saml2_logged_in'))
    return render(request, 'sso/logged-out.html')


@login_required
def session_logout(request):
    """
    Basic logout that destroys session to  logout the user and remove any saml2
    remnants.
    """
    request.session.flush()

    came_from = request.GET.get('next', settings.LOGOUT_REDIRECT_URL)
    if not came_from:
        logger.warning('The next parameter exists but is empty')
        came_from = settings.LOGIN_REDIRECT_URL

    return redirect(came_from)
