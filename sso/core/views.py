import datetime
import hmac
import uuid
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.db.models.functions import Now
from django.urls import reverse
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


    #############
    ## Get cursor

    after_ts_str, after_user_id_str = request.GET.get('cursor', '0.0_00000000-0000-4000-0000-000000000000').split('_')
    after_ts = datetime.datetime.fromtimestamp(float(after_ts_str))
    after_user_id = uuid.UUID(after_user_id_str)


    ##########################################################
    ## Fetch activities after cursor (i.e. user modifications)

    per_page = 50
    User = get_user_model()
    users = list(User.objects.only('user_id').extra(
        where=['(last_modified, user_id) > (%s, %s)', 'last_modified < STATEMENT_TIMESTAMP()'],
        params=(after_ts, after_user_id),
    ).order_by('last_modified', 'user_id')[:per_page])


    ################################################################
    ## Convert to activities, with link to next page if at least one

    def next_url(after_ts, after_user_id):
        return \
            request.build_absolute_uri(reverse('api-v1:core:activity-stream')) + \
            '?cursor={}_{}'.format(str(after_ts.timestamp()), str(after_user_id))

    page = {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            {'dit': 'https://www.trade.gov.uk/ns/activitystreams/v1'}
        ],
        'type': 'Collection',
        'orderedItems': [
            {
                'id': f'dit:StaffSSO:User:{user.user_id}:Update',
                'object': {
                    'id': f'dit:StaffSSO:User:{user.user_id}',
                }
            }
            for user in users
        ],
        **(
            {'next': next_url(users[-1].last_modified, users[-1].user_id)} if users \
            else {}
        )
    }

    return JsonResponse(
        data=page,
        status=200,
    )
