from django.db import models
from django.conf import settings

class ZoomMeeting(models.Model):
    MEETING_TYPE_CHOICES = (
        ('interview', 'Interview (60 min)'),
        ('onboarding', 'Onboarding (45 min)'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('started', 'Started'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    )
    
    # Reference the correct Application model
    application = models.ForeignKey(
        'application.Application',
        on_delete=models.CASCADE,
        related_name='zoom_meetings'
    )
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES)
    meeting_id = models.CharField(max_length=100, unique=True)
    join_url = models.URLField(max_length=500)
    start_url = models.URLField(max_length=500, blank=True)
    password = models.CharField(max_length=50, blank=True)
    start_time = models.DateTimeField()
    duration_minutes = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'zoom_meetings'
        ordering = ['-start_time']
        
    def __str__(self):
        return f"{self.get_meeting_type_display()} - {self.application.user.email}"