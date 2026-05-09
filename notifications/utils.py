from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Notification

def send_notification_email_sync(notification_id):
    """Send email for a notification (synchronous version)"""
    try:
        notification = Notification.objects.select_related('user').get(id=notification_id)
        
        # Check if user wants email notifications for this type
        prefs = notification.user.notification_preferences
        email_enabled = getattr(prefs, f'email_on_{notification.notification_type}', True)
        
        if not email_enabled:
            return
        
        subject = f"[RadiloxRemoteJobs] {notification.title}"
        
        html_content = render_to_string('emails/notification_email.html', {
            'user': notification.user,
            'notification': notification,
            'site_url': settings.SITE_URL,
        })
        
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_content,
            fail_silently=True,
        )
    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send notification email: {str(e)}")


# For Celery async tasks (if you have Celery set up)
# from celery import shared_task
# 
# @shared_task
# def send_notification_email(notification_id):
#     send_notification_email_sync(notification_id)