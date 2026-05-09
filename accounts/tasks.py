from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import User

@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            subject='Welcome to RadiloxRemoteJobs!',
            message=f'Hi {user.first_name or user.username},\n\nWelcome to RadiloxRemoteJobs! Start your journey today.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        return f"Welcome email sent to {user.email}"
    except User.DoesNotExist:
        return f"User {user_id} not found"

@shared_task
def check_expired_subscriptions():
    """Check and deactivate expired subscriptions"""
    from django.utils import timezone
    expired_users = User.objects.filter(
        is_subscription_active=True,
        subscription_expires_at__lt=timezone.now()
    )
    count = expired_users.update(is_subscription_active=False)
    return f"Deactivated {count} expired subscriptions"