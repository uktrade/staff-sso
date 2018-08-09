from django.utils.timezone import now


class UpdatedLastAccessedMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_response(self, request, response):
        if request.user.is_authenticated:
            last_accessed = now()
            request.user.last_accessed = last_accessed
            request.user.save()
        return response
