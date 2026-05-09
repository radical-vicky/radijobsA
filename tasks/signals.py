from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from notifications.models import create_notification

@receiver(post_save, sender=Task)
def task_notification(sender, instance, created, **kwargs):
    """Send notification when task is created or status changes"""
    if created:
        create_notification(
            user=instance.assigned_to,
            notification_type='task',
            title='New Task Assigned',
            message=f"You have been assigned a new task: {instance.title}",
            link=f'/tasks/{instance.id}/'
        )
    else:
        # Check if status changed
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            status_messages = {
                'submitted': f'Task "{instance.title}" has been submitted for review.',
                'approved': f'Task "{instance.title}" has been approved!',
                'paid': f'Payment of ${instance.budget_amount} has been processed for "{instance.title}".',
                'revision_requested': f'Revision requested for "{instance.title}". Please check the feedback.',
            }
            if instance.status in status_messages:
                create_notification(
                    user=instance.assigned_to if instance.status in ['submitted', 'revision_requested'] else instance.assigned_by,
                    notification_type='task',
                    title=f'Task {instance.status.replace("_", " ").title()}',
                    message=status_messages[instance.status],
                    link=f'/tasks/{instance.id}/'
                )