from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('application', 'Application Update'),
        ('quiz', 'Quiz Result'),
        ('task', 'Task Update'),
        ('payment', 'Payment Update'),
        ('subscription', 'Subscription Update'),
        ('system', 'System Message'),
        ('interview', 'Interview Scheduled'),
        ('onboarding', 'Onboarding Scheduled'),
        ('withdrawal', 'Withdrawal Update'),
    )
    
    STATUS_CHOICES = (
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('archived', 'Archived'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="URL to redirect when clicked")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread', db_index=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data like task_id, application_id, etc.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification_type']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.user.email} - {self.title[:50]}"
    
    def mark_as_read(self):
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at', 'updated_at'])
            return True
        return False
    
    def mark_as_unread(self):
        if self.status == 'read':
            self.status = 'unread'
            self.read_at = None
            self.save(update_fields=['status', 'read_at', 'updated_at'])
            return True
        return False
    
    def archive(self):
        self.status = 'archived'
        self.save(update_fields=['status', 'updated_at'])
    
    @property
    def is_read(self):
        return self.status == 'read'
    
    @property
    def time_ago(self):
        from django.utils.timesince import timesince
        return timesince(self.created_at)


class NotificationPreference(models.Model):
    """User preferences for which notifications they want to receive"""
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notifications
    email_on_application = models.BooleanField(default=True)
    email_on_quiz = models.BooleanField(default=True)
    email_on_task = models.BooleanField(default=True)
    email_on_payment = models.BooleanField(default=True)
    email_on_subscription = models.BooleanField(default=True)
    email_on_interview = models.BooleanField(default=True)
    email_on_withdrawal = models.BooleanField(default=True)
    
    # In-app notifications
    in_app_on_application = models.BooleanField(default=True)
    in_app_on_quiz = models.BooleanField(default=True)
    in_app_on_task = models.BooleanField(default=True)
    in_app_on_payment = models.BooleanField(default=True)
    in_app_on_subscription = models.BooleanField(default=True)
    in_app_on_interview = models.BooleanField(default=True)
    in_app_on_withdrawal = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        preference, created = cls.objects.get_or_create(user=user)
        return preference


# Helper function to create notifications
def create_notification(user, notification_type, title, message, link='', metadata=None, send_email=True):
    """
    Helper function to create a notification
    
    Usage:
        create_notification(
            user=request.user,
            notification_type='task',
            title='Task Completed',
            message='You have completed task #123',
            link='/tasks/123/',
            metadata={'task_id': 123}
        )
    """
    # Create in-app notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        metadata=metadata or {},
        status='unread'
    )
    
    # Send email if user wants it
    #if send_email:
      #  from .tasks import send_notification_email
      #  send_notification_email.delay(notification.id)
    
    return notification


def mark_all_as_read(user):
    """Mark all unread notifications as read for a user"""
    count = Notification.objects.filter(user=user, status='unread').update(
        status='read',
        read_at=timezone.now()
    )
    return count


def delete_old_notifications(days=90):
    """Delete notifications older than specified days"""
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    count = Notification.objects.filter(created_at__lt=cutoff_date).delete()
    return count