def notifications_processor(request):
    """
    Supplies the current user's unread notifications to all templates.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            from .models import Notification
            unread_qs = request.user.notifications.filter(is_read=False)
            return {
                'user_notifications': unread_qs[:6],
                'unread_notifications_count': unread_qs.count(),
            }
        except Exception:
            return {'user_notifications': [], 'unread_notifications_count': 0}
    return {'user_notifications': [], 'unread_notifications_count': 0}
