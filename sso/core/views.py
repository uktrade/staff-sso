import hmac
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from hawkserver import authenticate_hawk_header


@require_GET
@csrf_exempt
def activity_stream(request):
    def forbidden():
        return JsonResponse(
            data={},
            status=403,
        )


    ############################################
    ## Ensure not accessed via public networking

    via_public_internet = 'x-forwarded-for' in request.headers
    if via_public_internet:
        return forbidden()


    ###########################
    ## Ensure signed with Hawk

    def lookup_credentials(passed_id):
        user = {
            'id': settings.ACTIVITY_STREAM_HAWK_ID,
            'key':  settings.ACTIVITY_STREAM_HAWK_SECRET,
        }
        return \
            user if hmac.compare_digest(passed_id, user['id']) else \
            None

    def seen_nonce(nonce, id):
        # No replay attack prevention since no shared cache between instances,
        # but we're ok with that for now
        return False

    try:
        auth_header = request.headers['authorization']
    except KeyError:
        return forbidden()

    # This is brittle to not running in PaaS or not via private networking
    host, port = request.META['HTTP_HOST'].split(':')

    max_skew_seconds = 15
    error_message, credentials = authenticate_hawk_header(
        lookup_credentials, seen_nonce, max_skew_seconds,
        request.headers['authorization'],
        request.method, host, port, request.get_full_path(),
        request.headers.get('content-type', ''), request.body,
    )
    if error_message is not None:
        return forbidden()

    return JsonResponse(
        data={},
        status=200,
    )
