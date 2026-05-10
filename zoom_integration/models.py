from django.db import models
from django.conf import settings


class ZoomMeeting(models.Model):
    meeting_id = models.CharField(max_length=100, unique=True)
    topic = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    join_url = models.URLField()
    start_url = models.URLField()
    application = models.ForeignKey('application.Application', on_delete=models.SET_NULL, null=True, blank=True, related_name='zoom_meetings')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.topic} - {self.start_time}"