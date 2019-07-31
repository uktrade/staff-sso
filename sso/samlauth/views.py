import base64
import datetime as dt
import logging

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseRedirect,
    HttpResponseServerError
)
from django.shortcuts import render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import is_safe_url
from django.utils.six import text_type
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied, SuspiciousOperation

from djangosaml2.cache import IdentityCache, OutstandingQueriesCache, StateCache
from djangosaml2.conf import get_config
from djangosaml2.utils import (
    available_idps, fail_acs_response, get_custom_setting,
    get_idp_sso_supported_bindings, get_location, is_safe_url_compat,
)
from djangosaml2.views import _get_subject_id, _set_subject_id, finish_logout
from djangosaml2.signals import post_authenticated

from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.sigver import MissingKey
from saml2.client import Saml2Client
from saml2.s_utils import UnsupportedBinding
from saml2.xmldsig import SIG_RSA_SHA256
from saml2.response import (
    StatusError, StatusAuthnFailed, SignatureError, StatusRequestDenied,
    UnsolicitedResponse,
)
from saml2.validate import ResponseLifetimeExceed, ToEarly

from sso.core.logging import create_x_access_log


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
    if not is_safe_url(url=came_from, allowed_hosts=settings.ALLOWED_HOSTS):
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
    if not request.user.is_anonymous:
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

    last_login_idp = request.COOKIES.get('last_login_idp', None)

    # is a embedded wayf needed?
    idps = available_idps(conf)
    if selected_idp is None and len(idps) > 1:
        if last_login_idp and last_login_idp in idps:

            logger.debug('Re-authenticating against: %s', last_login_idp)
            selected_idp = last_login_idp

        else:
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
                    'SAMLRequest': base64.b64encode(force_bytes(request_xml)).decode('utf-8'),
                    'RelayState': came_from,
                },
            })
    else:
        raise UnsupportedBinding('Unsupported binding: %s', binding)

    # success, so save the session ID and return our response
    logger.debug('Saving the session_id in the OutstandingQueries cache')
    oq_cache = OutstandingQueriesCache(request.session)
    oq_cache.set(session_id, came_from)

    # Remove the last logged in cookie:
    # this will be set again at the end of the ACS call, if the user successfully authenticates.
    http_response.delete_cookie('last_login_idp')

    return http_response


@require_POST
@csrf_exempt
def assertion_consumer_service(request,
                               config_loader_path=None,
                               attribute_mapping=None,
                               create_unknown_user=None):
    """SAML Authorization Response endpoint

    The IdP will send its response to this view, which
    will process it with pysaml2 help and log the user
    in using the custom Authorization backend
    djangosaml2.backends.Saml2Backend that should be
    enabled in the settings.py
    """

    attribute_mapping = attribute_mapping or get_custom_setting('SAML_ATTRIBUTE_MAPPING', {'uid': ('username', )})
    create_unknown_user = create_unknown_user if create_unknown_user is not None else \
                          get_custom_setting('SAML_CREATE_UNKNOWN_USER', True)
    conf = get_config(config_loader_path, request)
    try:
        xmlstr = request.POST['SAMLResponse']
    except KeyError:
        logger.warning('Missing "SAMLResponse" parameter in POST data.')
        raise SuspiciousOperation

    client = Saml2Client(conf, identity_cache=IdentityCache(request.session))

    oq_cache = OutstandingQueriesCache(request.session)
    outstanding_queries = oq_cache.outstanding_queries()

    try:
        response = client.parse_authn_request_response(xmlstr, BINDING_HTTP_POST, outstanding_queries)
    except (StatusError, ToEarly):
        logger.exception("Error processing SAML Assertion.")
        return fail_acs_response(request)
    except ResponseLifetimeExceed:
        logger.info("SAML Assertion is no longer valid. Possibly caused by network delay or replay attack.", exc_info=True)
        return fail_acs_response(request)
    except SignatureError:
        logger.info("Invalid or malformed SAML Assertion.", exc_info=True)
        return fail_acs_response(request)
    except StatusAuthnFailed:
        logger.info("Authentication denied for user by IdP.", exc_info=True)
        return fail_acs_response(request)
    except StatusRequestDenied:
        logger.warning("Authentication interrupted at IdP.", exc_info=True)
        return fail_acs_response(request)
    except MissingKey:
        logger.exception("SAML Identity Provider is not configured correctly: certificate key is missing!")
        return fail_acs_response(request)
    except UnsolicitedResponse:
        logger.exception("Received SAMLResponse when no request has been made.")
        return fail_acs_response(request)

    if response is None:
        logger.warning("Invalid SAML Assertion received (unknown error).")
        return fail_acs_response(request, status=400, exc_class=SuspiciousOperation)

    session_id = response.session_id()
    oq_cache.delete(session_id)

    # authenticate the remote user
    session_info = response.session_info()

    if callable(attribute_mapping):
        attribute_mapping = attribute_mapping()
    if callable(create_unknown_user):
        create_unknown_user = create_unknown_user()

    logger.debug('Trying to authenticate the user. Session info: %s', session_info)
    user = auth.authenticate(request=request,
                             session_info=session_info,
                             attribute_mapping=attribute_mapping,
                             create_unknown_user=create_unknown_user)
    if user is None:
        logger.warning("Could not authenticate user received in SAML Assertion. Session info: %s", session_info)
        raise PermissionDenied

    auth.login(request, user)
    _set_subject_id(request.session, session_info['name_id'])
    logger.debug("User %s authenticated via SSO.", user)

    email = session_info['ava'].get('email', 'undefined')

    create_x_access_log(request, 200, message='Remote IdP Auth', entity_id=session_info['issuer'], email=email)

    logger.debug('Sending the post_authenticated signal')
    post_authenticated.send_robust(sender=user, session_info=session_info)

    # redirect the user to the view where he came from
    default_relay_state = get_custom_setting('ACS_DEFAULT_REDIRECT_URL',
                                             settings.LOGIN_REDIRECT_URL)
    relay_state = request.POST.get('RelayState', default_relay_state)
    if not relay_state:
        logger.warning('The RelayState parameter exists but is empty')
        relay_state = default_relay_state
    if not is_safe_url_compat(url=relay_state, allowed_hosts={request.get_host()}):
        relay_state = settings.LOGIN_REDIRECT_URL
    logger.debug('Redirecting to the RelayState: %s', relay_state)

    http_response = HttpResponseRedirect(relay_state)

    # remember the idp the user authenticated against
    http_response.set_cookie('last_login_idp', session_info['issuer'], expires=dt.datetime.today()+dt.timedelta(days=7))

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
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('saml2_logged_in'))
    return render(request, 'sso/logged-out.html')
