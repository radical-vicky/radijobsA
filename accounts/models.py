from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('applicant', 'Applicant'),
        ('freelancer', 'Freelancer'),
    )
    
    # Basic info
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='applicant')
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Contact info
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Social links
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    
    # Skills (JSON or Text field)
    skills = models.TextField(blank=True, null=True, help_text="Comma-separated list of skills")
    
    # Subscription fields
    has_active_subscription = models.BooleanField(default=False)
    subscription_expires_at = models.DateTimeField(blank=True, null=True)
    subscription_started_at = models.DateTimeField(blank=True, null=True)
    
    # Payment gateway fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['has_active_subscription']),
        ]
    
    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_applicant(self):
        return self.role == 'applicant'
    
    @property
    def is_freelancer(self):
        return self.role == 'freelancer'
    
    @property
    def subscription_is_active(self):
        """Check if subscription is active and not expired"""
        if not self.has_active_subscription:
            return False
        if self.subscription_expires_at and self.subscription_expires_at < timezone.now():
            # Auto-deactivate expired subscription
            self.has_active_subscription = False
            self.save(update_fields=['has_active_subscription'])
            return False
        return True
    
    def activate_subscription(self, duration_days=30):
        """
        Activate subscription for the user
        
        Args:
            duration_days: Number of days the subscription is valid for (default 30)
        """
        from notifications.models import create_notification
        
        self.has_active_subscription = True
        self.subscription_started_at = timezone.now()
        self.subscription_expires_at = timezone.now() + timedelta(days=duration_days)
        self.save()
        
        # Create notification
        create_notification(
            user=self,
            notification_type='subscription',
            title='Subscription Activated',
            message=f'Your premium subscription is now active until {self.subscription_expires_at.strftime("%B %d, %Y")}. You can now apply to unlimited jobs!',
            link='/subscriptions/status/'
        )
    
    def deactivate_subscription(self):
        """Deactivate subscription for the user"""
        from notifications.models import create_notification
        
        self.has_active_subscription = False
        self.save()
        
        # Create notification
        create_notification(
            user=self,
            notification_type='subscription',
            title='Subscription Deactivated',
            message='Your premium subscription has been deactivated.',
            link='/subscriptions/'
        )
    
    def extend_subscription(self, additional_days=30):
        """Extend an existing subscription"""
        if self.subscription_expires_at and self.subscription_expires_at > timezone.now():
            self.subscription_expires_at = self.subscription_expires_at + timedelta(days=additional_days)
        else:
            self.subscription_expires_at = timezone.now() + timedelta(days=additional_days)
        
        self.has_active_subscription = True
        self.save()
        
        from notifications.models import create_notification
        create_notification(
            user=self,
            notification_type='subscription',
            title='Subscription Extended',
            message=f'Your subscription has been extended until {self.subscription_expires_at.strftime("%B %d, %Y")}.',
            link='/subscriptions/status/'
        )
    
    def get_full_name(self):
        """Return the full name of the user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_initials(self):
        """Get user initials for avatar fallback"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()


class UserPaymentMethod(models.Model):
    PAYMENT_TYPES = (
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_account', 'Bank Account'),
        ('mpesa', 'M-Pesa'),
        ('binance', 'Binance Pay'),
        ('okx', 'OKX Pay'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # For credit/debit cards
    last_four = models.CharField(max_length=4, blank=True)
    card_holder_name = models.CharField(max_length=100, blank=True)
    expiry_month = models.IntegerField(null=True, blank=True)
    expiry_year = models.IntegerField(null=True, blank=True)
    
    # For PayPal and other online payments
    account_email = models.EmailField(blank=True, help_text="PayPal email or account email")
    
    # For M-Pesa
    phone_number = models.CharField(max_length=20, blank=True, help_text="Phone number for M-Pesa")
    
    # For Binance/OKX
    wallet_address = models.CharField(max_length=255, blank=True, help_text="Crypto wallet address")
    
    # Bank account fields
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_swift_code = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_user_payment_method'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_payment_type_display()}"
    
    def save(self, *args, **kwargs):
        # If this is the first payment method, make it default
        if not UserPaymentMethod.objects.filter(user=self.user).exists():
            self.is_default = True
        super().save(*args, **kwargs)