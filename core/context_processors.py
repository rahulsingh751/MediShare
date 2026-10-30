from django.conf import settings


def notification_count(request):
    base = {
        "request_workflows_enabled": settings.MEDISHARE_REQUEST_WORKFLOWS_ENABLED
    }
    if request.user.is_authenticated:
        return {
            **base,
            "unread_notification_count": request.user.notifications.filter(
                is_read=False
            ).count()
        }
    return {**base, "unread_notification_count": 0}
