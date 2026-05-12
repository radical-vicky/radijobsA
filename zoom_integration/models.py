from django.db import models
from django.conf import settings
from django.utils import timezone


class ZoomMeeting(models.Model):
    MEETING_TYPES = (
        ('interview', 'Interview'),
        ('onboarding', 'Onboarding'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='zoom_meetings')
    application = models.ForeignKey('application.Application', on_delete=models.CASCADE, null=True, blank=True, related_name='zoom_meetings')
    meeting_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPES, default='interview')
    start_time = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    join_url = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    postpone_reason = models.TextField(blank=True, null=True, help_text="Reason for postponement")
    rescheduled_date = models.DateTimeField(blank=True, null=True, help_text="New date for rescheduled meeting")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.topic} - {self.start_time} ({self.status})"
    
    def cancel(self):
        """Cancel the meeting"""
        self.status = 'cancelled'
        self.save()
        
        if self.application and self.application.status == 'interview_scheduled':
            self.application.status = 'approved'
            self.application.interview_link = None
            self.application.interview_scheduled_at = None
            self.application.save()
    
    def postpone(self, reason=None):
        """Postpone the meeting with a reason"""
        self.status = 'postponed'
        if reason:
            self.postpone_reason = reason
        self.save()
    
    def reschedule(self, new_datetime, new_join_url=None):
        """Reschedule a postponed meeting"""
        self.status = 'scheduled'
        self.start_time = new_datetime
        self.postpone_reason = None
        self.rescheduled_date = new_datetime
        if new_join_url:
            self.join_url = new_join_url
        self.save()
        
        if self.application:
            self.application.interview_scheduled_at = new_datetime
            if new_join_url:
                self.application.interview_link = new_join_url
            self.application.status = 'interview_scheduled'
            self.application.save()
    
    def mark_ongoing(self):
        """Mark meeting as ongoing"""
        self.status = 'ongoing'
        self.save()
    
    def mark_completed(self):
        """Mark meeting as completed"""
        self.status = 'completed'
        self.save()
        
        if self.application:
            self.application.interview_completed = True
            self.application.save()
    
    @property
    def is_upcoming(self):
        return self.start_time > timezone.now() and self.status == 'scheduled'
    
    @property
    def is_ongoing(self):
        return self.status == 'ongoing'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def is_cancelled(self):
        return self.status == 'cancelled'
    
    @property
    def is_postponed(self):
        return self.status == 'postponed'