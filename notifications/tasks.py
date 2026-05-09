from celery import shared_task
from .utils import send_notification_email_sync

@shared_task
def send_notification_email(notification_id):
    """Send notification email asynchronously with Celery"""
    send_notification_email_sync(notification_id)


@shared_task
def cleanup_old_notifications(days=90):
    """Periodic task to clean up old notifications"""
    from .models import delete_old_notifications
    count = delete_old_notifications(days)
    return f"Deleted {count} old notifications"