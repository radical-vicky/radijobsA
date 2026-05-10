from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from decimal import Decimal


@receiver(post_save, sender=Task)
def update_wallet_on_task_paid(sender, instance, created, **kwargs):
    """Automatically update wallet when task status changes to paid"""
    if not created and instance.status == 'paid':
        # Check if this is a status change to paid
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != 'paid':
                from wallet.models import UserWallet, Transaction
                from notifications.models import Notification
                from django.core.mail import send_mail
                from django.conf import settings
                
                amount = Decimal(str(instance.budget_amount))
                
                wallet, created = UserWallet.objects.get_or_create(user=instance.assigned_to)
                
                wallet.balance += amount
                wallet.total_earned += amount
                wallet.save()
                
                Transaction.objects.create(
                    user=instance.assigned_to,
                    transaction_type='task_payment',
                    amount=amount,
                    fee=0,
                    net_amount=amount,
                    description=f"Payment for task: {instance.title} (Job: {instance.job.title})",
                    reference_id=str(instance.id)
                )
                
                Notification.objects.create(
                    user=instance.assigned_to,
                    notification_type='payment',
                    title='Payment Received',
                    message=f"${amount} has been added to your wallet for task: {instance.title}. New balance: ${wallet.balance}",
                    link='/wallet/',
                    status='unread'
                )
                
                send_mail(
                    subject=f"Payment Received - {instance.title}",
                    message=f"""
Dear {instance.assigned_to.get_full_name() or instance.assigned_to.username},

You have received a payment of ${amount} for task: {instance.title}

Current Wallet Balance: ${wallet.balance}

View your wallet: http://127.0.0.1:8000/wallet/

Thank you for your hard work!

Best regards,
RadiloxRemoteJobs Team
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.assigned_to.email],
                    fail_silently=False
                )
        except sender.DoesNotExist:
            pass