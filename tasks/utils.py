# tasks/utils.py
from decimal import Decimal


def process_task_payment(task):
    """Process task payment - updates wallet, creates transaction, sends notifications"""
    from wallet.models import UserWallet, Transaction
    from notifications.models import Notification
    from django.core.mail import send_mail
    from django.conf import settings
    
    if task.status != 'approved':
        return False
    
    amount = Decimal(str(task.budget_amount))
    
    # Get or create wallet
    wallet, created = UserWallet.objects.get_or_create(user=task.assigned_to)
    
    # Update wallet
    wallet.balance += amount
    wallet.total_earned += amount
    wallet.save()
    
    # Create transaction
    Transaction.objects.create(
        user=task.assigned_to,
        transaction_type='task_payment',
        amount=amount,
        fee=0,
        net_amount=amount,
        description=f"Payment for task: {task.title} (Job: {task.job.title})",
        reference_id=str(task.id)
    )
    
    # Mark task as paid
    task.mark_paid()
    
    # Send notification
    Notification.objects.create(
        user=task.assigned_to,
        notification_type='payment',
        title='Payment Received',
        message=f"${amount} has been added to your wallet for task: {task.title}. New balance: ${wallet.balance}",
        link='/wallet/',
        status='unread'
    )
    
    # Send email
    send_mail(
        subject=f"Payment Received - {task.title}",
        message=f"""
Dear {task.assigned_to.get_full_name() or task.assigned_to.username},

You have received a payment of ${amount} for task: {task.title}

Current Wallet Balance: ${wallet.balance}

View your wallet: http://127.0.0.1:8000/wallet/

Thank you for your hard work!

Best regards,
RadiloxRemoteJobs Team
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[task.assigned_to.email],
        fail_silently=False
    )
    
    return True