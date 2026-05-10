from django.contrib import admin
from .models import ZoomMeeting


@admin.register(ZoomMeeting)
class ZoomMeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'start_time', 'duration_minutes', 'application', 'created_at')
    list_filter = ('start_time', 'created_at')
    search_fields = ('topic', 'meeting_id', 'application__user__email')
    readonly_fields = ('meeting_id', 'created_at')
    
    fieldsets = (
        ('Meeting Information', {
            'fields': ('meeting_id', 'topic', 'start_time', 'duration_minutes')
        }),
        ('Links', {
            'fields': ('join_url', 'start_url'),
            'classes': ('collapse',)
        }),
        ('Application', {
            'fields': ('application',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )