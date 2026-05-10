from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class Task(models.Model):
    STATUS_CHOICES = (
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved - Pending Payment'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
    )
    
    # Relationships
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    
    # Task details
    title = models.CharField(max_length=255)
    description = models.TextField()
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Task Image
    image = models.ImageField(upload_to='task_images/%Y/%m/%d/', blank=True, null=True, help_text="Task preview image")
    image_url = models.URLField(blank=True, null=True, help_text="External image URL for task preview")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    # Dates
    deadline = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Submission
    submission_url = models.URLField(blank=True, help_text="GitHub repository or deployed URL")
    submission_notes = models.TextField(blank=True, help_text="Additional notes about the submission")
    
    # Revisions
    revision_feedback = models.TextField(blank=True, help_text="Feedback for revisions")
    revision_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['job', 'status']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.assigned_to.email} - {self.status}"
    
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        elif self.image_url:
            return self.image_url
        return None
    
    def start_task(self):
        if self.status == 'assigned':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save()
            return True
        return False
    
    def submit_task(self, submission_url, submission_notes):
        if self.status in ['assigned', 'in_progress', 'revision_requested']:
            self.status = 'submitted'
            self.submission_url = submission_url
            self.submission_notes = submission_notes
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False
    
    def approve_task(self):
        if self.status == 'submitted':
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()
            return True
        return False
    
    def mark_paid(self):
        """Mark task as paid and automatically update wallet, create transaction, send notification and email"""
        if self.status == 'approved':
            from wallet.models import UserWallet, Transaction
            from notifications.models import Notification
            from django.core.mail import send_mail
            
            amount = Decimal(str(self.budget_amount))
            
            # Get or create wallet for the user
            wallet, created = UserWallet.objects.get_or_create(user=self.assigned_to)
            
            # Update wallet balance
            wallet.balance += amount
            wallet.total_earned += amount
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=self.assigned_to,
                transaction_type='task_payment',
                amount=amount,
                fee=0,
                net_amount=amount,
                description=f"Payment for task: {self.title} (Job: {self.job.title})",
                reference_id=str(self.id)
            )
            
            # Update task status
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save()
            
            # Send in-app notification
            Notification.objects.create(
                user=self.assigned_to,
                notification_type='payment',
                title='Payment Received',
                message=f"${amount} has been added to your wallet for task: {self.title}. New balance: ${wallet.balance}",
                link='/wallet/',
                status='unread'
            )
            
            # Send email notification
            send_mail(
                subject=f"Payment Received - {self.title}",
                message=f"""
Dear {self.assigned_to.get_full_name() or self.assigned_to.username},

You have received a payment of ${amount} for task: {self.title}

Current Wallet Balance: ${wallet.balance}

View your wallet: http://127.0.0.1:8000/wallet/

Thank you for your hard work!

Best regards,
RadiloxRemoteJobs Team
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.assigned_to.email],
                fail_silently=False
            )
            
            return True
        return False
    
    def request_revision(self, feedback):
        if self.status == 'submitted':
            self.status = 'revision_requested'
            self.revision_feedback = feedback
            self.revision_count += 1
            self.save()
            return True
        return False
    
    def reject_task(self, reason):
        if self.status == 'submitted':
            self.status = 'rejected'
            self.revision_feedback = reason
            self.save()
            return True
        return False


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_attachments'
        
    def __str__(self):
        return self.filename


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    is_admin_note = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_comments'
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.user.email} on {self.task.title}"