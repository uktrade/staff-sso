from django.conf import settings


def template_settings(request):
    return {
        'GOOGLE_ANALYTICS_CODE': getattr(settings, 'GOOGLE_ANALYTICS_CODE', None)
    }
