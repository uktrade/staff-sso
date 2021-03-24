import datetime as dt
import json
import logging

from django.conf import settings

from .ip_filter import get_client_ip


logger = logging.getLogger("x-auth")


def create_x_access_log(request, status_code, message="", **extra_fields):
    """
    Create a x-application access log. See DIT manual `cross application logging` for more information.
    """

    user = getattr(request, "user", None)

    log = {
        "request_id": "",
        "request_time": str(dt.datetime.utcnow()),
        "sso_user_id": str(user.user_id) if user else None,
        "local_user_id": user.id if user else None,
        "path": request.path,
        "url": {"domain": request.get_host()},
        "status": status_code,
        "ip": get_client_ip(request),
        "message": message,
        "service": "staff-sso {}".format(settings.ENV_NAME),
    }

    log.update(**extra_fields)

    logger.info(json.dumps(log))
