import logging


logger = logging.getLogger(__file__)


def get_client_ip(request):
    try:
        return request.META['HTTP_X_FORWARDED_FOR'].split(',')[-3].strip()
    except (IndexError, KeyError):
        logger.warning(
            'X-Forwarded-For header is missing or does not '
            'contain enough elements to determine the '
            'client\'s ip')
        return None
