from django.utils.timezone import now


class UpdatedLastAccessedMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        self.set_last_accessed_date(request)

        return self.get_response(request)

    def set_last_accessed_date(self, request):
        if request.user.is_authenticated:
            request.user.last_accessed = now()
            request.user.save(update_fields=["last_accessed"])
