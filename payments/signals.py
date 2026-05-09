from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PaymentTransaction
from notifications.models import create_notification

@receiver(post_save, sender=PaymentTransaction)
def payment_notification(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.user,
            notification_type='payment',
            title='Payment Initiated',
            message=f"Your {instance.payment_type} payment of ${instance.amount} has been initiated.",
            link=f'/payments/status/{instance.id}/'
        )
    elif instance.status == 'completed':
        create_notification(
            user=instance.user,
            notification_type='payment',
            title='Payment Completed',
            message=f"Your {instance.payment_type} payment of ${instance.amount} was successful!",
            link=f'/payments/status/{instance.id}/'
        )
    elif instance.status == 'failed':
        create_notification(
            user=instance.user,
            notification_type='payment',
            title='Payment Failed',
            message=f"Your {instance.payment_type} payment of ${instance.amount} failed. Please try again.",
            link=f'/payments/subscribe/'
        )