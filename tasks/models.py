from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

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
    
    def start_task(self):
        """Mark task as in progress"""
        if self.status == 'assigned':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save()
            return True
        return False
    
    def submit_task(self, submission_url, submission_notes):
        """Submit task for review"""
        if self.status in ['assigned', 'in_progress', 'revision_requested']:
            self.status = 'submitted'
            self.submission_url = submission_url
            self.submission_notes = submission_notes
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False
    
    def approve_task(self):
        """Approve task - ready for payment"""
        if self.status == 'submitted':
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()
            return True
        return False
    
    def mark_paid(self):
        """Mark task as paid"""
        if self.status == 'approved':
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save()
            return True
        return False
    
    def request_revision(self, feedback):
        """Request revision from freelancer"""
        if self.status == 'submitted':
            self.status = 'revision_requested'
            self.revision_feedback = feedback
            self.revision_count += 1
            self.save()
            return True
        return False
    
    def reject_task(self, reason):
        """Reject task completely"""
        if self.status == 'submitted':
            self.status = 'rejected'
            self.revision_feedback = reason
            self.save()
            return True
        return False

class TaskAttachment(models.Model):
    """Files attached to tasks (screenshots, documents, etc.)"""
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
    """Comments and discussions on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    is_admin_note = models.BooleanField(default=False)  # Private admin note
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_comments'
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.user.email} on {self.task.title}"