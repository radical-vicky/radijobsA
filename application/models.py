from django.db import models
from django.conf import settings
from django.utils import timezone


class Application(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='applications')
    
    # Personal info
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Application details
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    portfolio_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Additional info
    years_experience = models.CharField(max_length=50, blank=True)
    notice_period = models.CharField(max_length=50, blank=True)
    additional_notes = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Quiz fields
    quiz_score = models.IntegerField(null=True, blank=True)
    quiz_taken_at = models.DateTimeField(null=True, blank=True)
    quiz_expires_at = models.DateTimeField(null=True, blank=True)
    quiz_duration_minutes = models.IntegerField(default=30)
    
    # Interview fields
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_zoom_link = models.CharField(max_length=500, blank=True)
    
    # Onboarding fields
    onboarding_date = models.DateTimeField(null=True, blank=True)
    onboarding_zoom_link = models.CharField(max_length=500, blank=True)
    
    # Hiring fields
    hired_at = models.DateTimeField(null=True, blank=True)
    is_active_employment = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title}"
    
    def has_quiz_expired(self):
        if self.quiz_expires_at:
            return timezone.now() > self.quiz_expires_at
        return False