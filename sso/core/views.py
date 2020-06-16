from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt


@require_GET
@csrf_exempt
def activity_stream(request):
    return JsonResponse(
        data={},
        status=200,
    )
