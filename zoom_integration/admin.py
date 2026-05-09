from django.contrib import admin
from .models import ZoomMeeting

@admin.register(ZoomMeeting)
class ZoomMeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'meeting_type', 'meeting_id', 'start_time', 'status', 'created_at')
    list_filter = ('meeting_type', 'status', 'start_time')
    search_fields = ('meeting_id', 'application__user__email', 'application__job__title')
    readonly_fields = ('meeting_id', 'join_url', 'start_url', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Meeting Information', {
            'fields': ('application', 'meeting_type', 'meeting_id', 'join_url', 'start_url', 'password')
        }),
        ('Schedule', {
            'fields': ('start_time', 'duration_minutes', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )