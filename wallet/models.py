from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class UserWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_wallets'
    
    def __str__(self):
        return f"{self.user.username} - Balance: ${self.balance}"
    
    def add_funds(self, amount, description, reference_id=None):
        from wallet.models import Transaction
        from notifications.models import Notification
        
        amount = Decimal(str(amount))
        self.balance += amount
        self.total_earned += amount
        self.save()
        
        Transaction.objects.create(
            user=self.user,
            transaction_type='deposit',
            amount=amount,
            fee=0,
            net_amount=amount,
            description=description,
            reference_id=reference_id
        )
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Funds Added to Wallet',
            message=f'${amount} has been added to your wallet. New balance: ${self.balance}',
            link='/wallet/',
            status='unread'
        )
        
        return True
    
    def deduct_funds(self, amount, description, reference_id=None):
        from wallet.models import Transaction
        from notifications.models import Notification
        
        amount = Decimal(str(amount))
        
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        
        self.balance -= amount
        self.total_withdrawn += amount
        self.save()
        
        Transaction.objects.create(
            user=self.user,
            transaction_type='withdrawal',
            amount=amount,
            fee=0,
            net_amount=amount,
            description=description,
            reference_id=reference_id
        )
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Withdrawal Processed',
            message=f'${amount} has been deducted from your wallet. New balance: ${self.balance}',
            link='/wallet/',
            status='unread'
        )
        
        return True
    
    def add_task_payment(self, task):
        from wallet.models import Transaction
        from notifications.models import Notification
        from django.core.mail import send_mail
        
        amount = Decimal(str(task.budget_amount))
        
        self.balance += amount
        self.total_earned += amount
        self.save()
        
        Transaction.objects.create(
            user=self.user,
            transaction_type='task_payment',
            amount=amount,
            fee=0,
            net_amount=amount,
            description=f"Payment for task: {task.title} (Job: {task.job.title})",
            reference_id=str(task.id)
        )
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Payment Received',
            message=f'${amount} has been added to your wallet for task: {task.title}. New balance: ${self.balance}',
            link='/wallet/',
            status='unread'
        )
        
        send_mail(
            subject=f"Payment Received - {task.title}",
            message=f"""
Dear {self.user.get_full_name() or self.user.username},

You have received a payment of ${amount} for task: {task.title}

Current Wallet Balance: ${self.balance}

View your wallet: http://127.0.0.1:8000/wallet/

Thank you for your hard work!

Best regards,
RadiloxRemoteJobs Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False
        )
        
        return True


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('task_payment', 'Task Payment'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.get_transaction_type_display()}"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHODS = (
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa'),
        ('bank_account', 'Bank Account'),
        ('crypto', 'Cryptocurrency'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    destination_details = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'withdrawal_requests'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"
    
    def process_withdrawal(self):
        from wallet.models import UserWallet
        from notifications.models import Notification
        
        wallet = UserWallet.objects.get(user=self.user)
        
        if wallet.balance < self.amount:
            self.status = 'failed'
            self.admin_notes = "Insufficient balance"
            self.save()
            return False
        
        wallet.balance -= self.amount
        wallet.total_withdrawn += self.amount
        wallet.save()
        
        Transaction.objects.create(
            user=self.user,
            transaction_type='withdrawal',
            amount=self.amount,
            fee=self.fee,
            net_amount=self.net_amount,
            description=f"Withdrawal via {self.get_payment_method_display()}",
            reference_id=str(self.id)
        )
        
        self.status = 'processing'
        self.processed_at = timezone.now()
        self.save()
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Withdrawal Processing',
            message=f'Your withdrawal request of ${self.amount} is being processed. New balance: ${wallet.balance}',
            link='/wallet/',
            status='unread'
        )
        
        return True
    
    def complete_withdrawal(self):
        from notifications.models import Notification
        from django.core.mail import send_mail
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Withdrawal Completed',
            message=f'Your withdrawal of ${self.amount} has been completed and sent to your {self.get_payment_method_display()} account.',
            link='/wallet/withdrawal-history/',
            status='unread'
        )
        
        send_mail(
            subject="Withdrawal Completed",
            message=f"""
Dear {self.user.get_full_name() or self.user.username},

Your withdrawal of ${self.amount} has been completed successfully.

Payment Method: {self.get_payment_method_display()}
Amount: ${self.amount}
Fee: ${self.fee}
Net Amount: ${self.net_amount}

The funds have been sent to your {self.get_payment_method_display()} account.

Thank you for using RadiloxRemoteJobs!

Best regards,
RadiloxRemoteJobs Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            fail_silently=False
        )
        
        return True
    
    def fail_withdrawal(self, reason):
        from wallet.models import UserWallet
        from notifications.models import Notification
        
        wallet = UserWallet.objects.get(user=self.user)
        wallet.balance += self.amount
        wallet.save()
        
        self.status = 'failed'
        self.admin_notes = reason
        self.save()
        
        Notification.objects.create(
            user=self.user,
            notification_type='payment',
            title='Withdrawal Failed',
            message=f'Your withdrawal of ${self.amount} has failed. Reason: {reason}. Funds have been returned to your wallet.',
            link='/wallet/',
            status='unread'
        )
        
        return True