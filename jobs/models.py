from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from cloudinary.models import CloudinaryField

class JobCategory(models.Model):
    """Job categories for better organization"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'job_categories'
        ordering = ['order', 'name']
        verbose_name = 'Job Category'
        verbose_name_plural = 'Job Categories'
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('jobs:category', args=[self.slug])


class Job(models.Model):
    JOB_TYPE_CHOICES = (
        ('freelance', 'Freelance'),
        ('fulltime', 'Full Time'),
        ('parttime', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    )
    
    EXPERIENCE_CHOICES = (
        ('entry', 'Entry Level (0-2 years)'),
        ('intermediate', 'Intermediate (2-5 years)'),
        ('senior', 'Senior (5-8 years)'),
        ('expert', 'Expert (8+ years)'),
    )
    
    # Basic Information
    title = models.CharField(max_length=255, db_index=True)
    company = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    requirements = models.TextField()
    project_brief = models.TextField(
        help_text="The project applicant must complete before interview",
        verbose_name="Project Brief (Required for Interview)"
    )
    
    # Categories
    categories = models.ManyToManyField(JobCategory, blank=True, related_name='jobs')
    
    # Compensation & Location
    salary_range = models.CharField(max_length=100, help_text="e.g., $80 - $100 per hour or $120k - $150k per year")
    location = models.CharField(max_length=255, default='Remote', db_index=True)
    
    # Classification
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='freelance', db_index=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='intermediate', db_index=True)
    skills_required = models.JSONField(default=list, blank=True, help_text="List of required skills")
    
    # Images
    image = CloudinaryField('job_image', blank=True, null=True, folder='job_images/', help_text="Upload job advertisement image")
    image_url = models.URLField(blank=True, help_text="External image URL (if not using Cloudinary upload)")
    company_logo = CloudinaryField('company_logo', blank=True, null=True, folder='company_logos/', help_text="Company logo image")
    
    # Deadlines
    application_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Deadline for submitting applications. Applicants cannot apply after this date."
    )
    
    # Status & Tracking
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True, help_text="Featured jobs appear on homepage")
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    application_count = models.PositiveIntegerField(default=0)
    
    # Relationships
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_jobs')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, help_text="When job was first published")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When job posting expires")
    
    class Meta:
        db_table = 'jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['job_type', '-created_at']),
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['location', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['application_deadline']),
        ]
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    def get_absolute_url(self):
        return reverse('jobs:detail', args=[self.id])
    
    @property
    def get_image_url(self):
        if self.image:
            return self.image.url
        elif self.image_url:
            return self.image_url
        return None
    
    @property
    def get_company_logo_url(self):
        if self.company_logo:
            return self.company_logo.url
        return None
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_application_deadline_passed(self):
        """Check if application deadline has passed"""
        if self.application_deadline:
            return timezone.now() > self.application_deadline
        return False
    
    @property
    def days_remaining(self):
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return None
    
    @property
    def application_deadline_remaining(self):
        """Get remaining time until application deadline as timedelta"""
        if self.application_deadline:
            delta = self.application_deadline - timezone.now()
            if delta.total_seconds() <= 0:
                return None
            return delta
        return None
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_application_count(self):
        self.application_count += 1
        self.save(update_fields=['application_count'])
    
    def publish(self):
        self.is_active = True
        if not self.published_at:
            self.published_at = timezone.now()
        self.save()
    
    def unpublish(self):
        self.is_active = False
        self.save()
    
    def save(self, *args, **kwargs):
        if self.is_active and not self.published_at:
            self.published_at = timezone.now()
        if not self.expires_at and self.is_active:
            self.expires_at = timezone.now() + timezone.timedelta(days=90)
        super().save(*args, **kwargs)


class SavedJob(models.Model):
    """Model for users to save jobs they're interested in"""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by_users')
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Personal notes about this job")
    
    class Meta:
        db_table = 'saved_jobs'
        ordering = ['-saved_at']
        unique_together = ['user', 'job']
        indexes = [
            models.Index(fields=['user', '-saved_at']),
        ]
        verbose_name = 'Saved Job'
        verbose_name_plural = 'Saved Jobs'
    
    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"