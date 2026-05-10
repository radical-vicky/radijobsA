from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class PaymentTransaction(models.Model):
    """Base model for all payment transactions"""
    
    PAYMENT_TYPE_CHOICES = (
        ('subscription', 'Subscription Payment'),
        ('withdrawal', 'Withdrawal Payment'),
        ('deposit', 'Deposit'),
        ('refund', 'Refund'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('binance', 'Binance Pay'),
        ('okx', 'OKX Pay'),
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('card', 'Credit/Debit Card'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    # User info
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_transactions')
    
    # Payment details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Crypto specific
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    crypto_currency = models.CharField(max_length=10, blank=True)
    crypto_address = models.CharField(max_length=255, blank=True)
    crypto_tx_hash = models.CharField(max_length=255, blank=True)
    
    # Transaction IDs
    transaction_id = models.CharField(max_length=255, unique=True, blank=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Webhook data
    webhook_payload = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['payment_type', 'status']),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.payment_type} - ${self.amount} - {self.status}"
    
    def mark_completed(self, gateway_tx_id=None, tx_hash=None):
        """Mark transaction as completed"""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gateway_tx_id:
            self.gateway_transaction_id = gateway_tx_id
        if tx_hash:
            self.crypto_tx_hash = tx_hash
        self.save()
    
    def mark_failed(self, error_message):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()
    
    def mark_processing(self):
        """Mark transaction as processing"""
        from django.utils import timezone
        self.status = 'processing'
        self.processed_at = timezone.now()
        self.save()





class PaymentWebhookLog(models.Model):
    """Log all incoming webhooks from payment gateways"""
    gateway = models.CharField(max_length=50)  # binance, paypal, mpesa, etc.
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_webhook_logs'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.gateway} - {self.event_type} - {self.created_at}"