from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt


@require_GET
@csrf_exempt
def activity_stream(request):
    def forbidden():
        return JsonResponse(
            data={},
            status=403,
        )

    via_public_internet = 'x-forwarded-for' in request.headers
    if via_public_internet:
        return forbidden()

    return JsonResponse(
        data={},
        status=200,
    )
