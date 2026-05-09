from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import URLValidator
from cloudinary.models import CloudinaryField

class ContactMessage(models.Model):
    SUBJECT_CHOICES = (
        ('general', 'General Inquiry'),
        ('hiring', 'Hiring / Post a Job'),
        ('freelancer', 'Becoming a Freelancer'),
        ('payment', 'Payment Issue'),
        ('technical', 'Technical Support'),
        ('partnership', 'Partnership Opportunity'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('complaint', 'Complaint'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('new', '🔴 New'),
        ('read', '🟡 Read'),
        ('replied', '🟢 Replied'),
        ('archived', '⚪ Archived'),
        ('spam', '⚠️ Spam'),
    )
    
    # Contact information
    name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, db_index=True)
    message = models.TextField()
    
    # Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admin")
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referred_from = models.URLField(blank=True, help_text="Page user was on before contact")
    
    # Response tracking
    response_message = models.TextField(blank=True, help_text="Admin's response message")
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_responses'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'contact_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email']),
            models.Index(fields=['subject']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def mark_as_read(self):
        if self.status == 'new':
            self.status = 'read'
            self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_replied(self, response_message=None, admin_user=None):
        self.status = 'replied'
        self.replied_at = timezone.now()
        if response_message:
            self.response_message = response_message
        if admin_user:
            self.responded_by = admin_user
        self.save(update_fields=['status', 'replied_at', 'response_message', 'responded_by', 'updated_at'])
    
    def mark_as_resolved(self):
        self.status = 'archived'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at', 'updated_at'])
    
    def mark_as_spam(self):
        self.status = 'spam'
        self.save(update_fields=['status', 'updated_at'])
    
    @property
    def is_new(self):
        return self.status == 'new'
    
    @property
    def response_time_hours(self):
        if self.replied_at and self.created_at:
            delta = self.replied_at - self.created_at
            return delta.total_seconds() / 3600
        return None


class ContactInfo(models.Model):
    """Dynamic contact information settings"""
    
    # Email settings
    support_email = models.EmailField(default='support@radiloxremotejobs.com')
    sales_email = models.EmailField(default='sales@radiloxremotejobs.com')
    careers_email = models.EmailField(default='careers@radiloxremotejobs.com')
    legal_email = models.EmailField(default='legal@radiloxremotejobs.com')
    privacy_email = models.EmailField(default='privacy@radiloxremotejobs.com')
    email_response_time = models.CharField(
        max_length=100, 
        default='Within 24 hours', 
        help_text="e.g., Within 24 hours"
    )
    
    # Phone settings
    phone_number = models.CharField(max_length=50, default='+1 (555) 123-4567')
    phone_hours = models.CharField(
        max_length=200, 
        default='Mon-Fri, 9am-6pm EST', 
        help_text="Phone availability hours"
    )
    phone_emergency = models.CharField(max_length=50, blank=True, help_text="Emergency contact number")
    
    # Live chat settings
    chat_enabled = models.BooleanField(default=True)
    chat_message = models.CharField(
        max_length=200, 
        default='Available on the platform', 
        help_text="Chat availability message"
    )
    chat_instruction = models.CharField(
        max_length=200, 
        default='Click the chat icon at the bottom right', 
        help_text="Chat instruction text"
    )
    chat_widget_code = models.TextField(blank=True, help_text="Embed code for chat widget")
    
    # Office hours
    monday_friday_hours = models.CharField(max_length=100, default='9:00 AM - 6:00 PM EST')
    saturday_hours = models.CharField(max_length=100, default='10:00 AM - 2:00 PM EST')
    sunday_hours = models.CharField(max_length=100, default='Closed')
    
    # Address & Map
    address = models.TextField(blank=True, help_text="Physical address")
    map_embed_url = models.URLField(blank=True, help_text="Google Maps embed URL")
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # FAQ section settings
    faq_section_title = models.CharField(max_length=200, default='Frequently asked questions')
    faq_section_subtitle = models.CharField(max_length=200, default='Find quick answers to common questions')
    faq_button_text = models.CharField(max_length=100, default='View all FAQs')
    
    # Newsletter settings
    newsletter_enabled = models.BooleanField(default=True)
    newsletter_title = models.CharField(max_length=200, default='Subscribe to our newsletter')
    newsletter_subtitle = models.CharField(max_length=200, default='Get the latest updates and offers')
    newsletter_button_text = models.CharField(max_length=100, default='Subscribe')
    
    # Social media presence
    twitter_handle = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    discord_url = models.URLField(blank=True)
    
    # Trust badges / certifications
    trust_badges = models.JSONField(default=list, blank=True, help_text="List of trust badges/certifications")
    
    # Last updated tracking
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_info_updates'
    )
    
    class Meta:
        db_table = 'contact_info'
        verbose_name = 'Contact Information'
        verbose_name_plural = 'Contact Information'
    
    def __str__(self):
        return "Contact Information Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and ContactInfo.objects.exists():
            raise ValueError("There can only be one ContactInfo instance")
        super().save(*args, **kwargs)


class SocialLink(models.Model):
    """Social media links for the contact page and footer"""
    
    PLATFORM_CHOICES = (
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('github', 'GitHub'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('discord', 'Discord'),
        ('slack', 'Slack'),
        ('telegram', 'Telegram'),
        ('whatsapp', 'WhatsApp'),
        ('medium', 'Medium'),
        ('devto', 'Dev.to'),
        ('stackoverflow', 'Stack Overflow'),
    )
    
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, db_index=True)
    url = models.URLField(validators=[URLValidator()])
    icon_class = models.CharField(max_length=100, blank=True, help_text="Optional: Custom icon class")
    order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=True)
    show_in_contact = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_links'
        ordering = ['order', 'platform']
        verbose_name = 'Social Link'
        verbose_name_plural = 'Social Links'
    
    def __str__(self):
        return f"{self.get_platform_display()} - {self.url}"


class FAQ(models.Model):
    """Frequently Asked Questions for the contact page and FAQ page"""
    
    CATEGORY_CHOICES = (
        ('general', 'General'),
        ('for_freelancers', 'For Freelancers'),
        ('for_employers', 'For Employers'),
        ('payments', 'Payments & Withdrawals'),
        ('technical', 'Technical Support'),
        ('account', 'Account & Security'),
        ('billing', 'Billing & Subscriptions'),
        ('jobs', 'Jobs & Applications'),
        ('tasks', 'Tasks & Projects'),
    )
    
    question = models.CharField(max_length=500, db_index=True)
    answer = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general', db_index=True)
    order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    views = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'faqs'
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['order']),
        ]
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question[:100]
    
    @property
    def helpful_percentage(self):
        total = self.helpful_count + self.not_helpful_count
        if total > 0:
            return (self.helpful_count / total) * 100
        return 0
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def mark_helpful(self):
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    def mark_not_helpful(self):
        self.not_helpful_count += 1
        self.save(update_fields=['not_helpful_count'])


class NewsletterSubscriber(models.Model):
    """Newsletter subscribers"""
    
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'newsletter_subscribers'
        ordering = ['-subscribed_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
    
    def __str__(self):
        return self.email
    
    def unsubscribe(self):
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=['is_active', 'unsubscribed_at'])


class SiteSettings(models.Model):
    """General site settings"""
    
    # Branding
    site_name = models.CharField(max_length=100, default='RadiloxRemoteJobs')
    site_tagline = models.CharField(max_length=200, default='Remote IT Talent Platform')
    site_logo = CloudinaryField('logo', blank=True, null=True, folder='brand/')
    site_favicon = CloudinaryField('favicon', blank=True, null=True, folder='brand/')
    
    # SEO
    meta_description = models.TextField(blank=True, help_text="Default meta description")
    meta_keywords = models.CharField(max_length=500, blank=True, help_text="Default meta keywords")
    google_analytics_id = models.CharField(max_length=50, blank=True)
    
    # Maintenance
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Contact
    contact_email = models.EmailField(default='contact@radiloxremotejobs.com')
    admin_email = models.EmailField(default='admin@radiloxremotejobs.com')
    
    # Social sharing
    twitter_card_image = CloudinaryField('twitter_card', blank=True, null=True, folder='seo/')
    facebook_og_image = CloudinaryField('facebook_og', blank=True, null=True, folder='seo/')
    
    # Updated tracking
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_settings_updates'
    )
    
    class Meta:
        db_table = 'site_settings'
        verbose_name = 'Site Setting'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return "Site Settings"
    
    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError("There can only be one SiteSettings instance")
        super().save(*args, **kwargs)