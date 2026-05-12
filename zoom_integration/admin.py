from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import ZoomMeeting


@admin.register(ZoomMeeting)
class ZoomMeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'topic', 'meeting_type', 'start_time', 'status_badge', 'join_link')
    list_filter = ('meeting_type', 'status', 'start_time')
    search_fields = ('user__username', 'user__email', 'topic', 'meeting_id')
    readonly_fields = ('created_at', 'updated_at', 'rescheduled_date')
    
    fieldsets = (
        ('Meeting Information', {
            'fields': ('user', 'application', 'topic', 'meeting_type', 'meeting_id')
        }),
        ('Schedule', {
            'fields': ('start_time', 'duration_minutes')
        }),
        ('Links', {
            'fields': ('join_url',)
        }),
        ('Postponement Details', {
            'fields': ('postpone_reason', 'rescheduled_date'),
            'classes': ('collapse',),
            'description': 'Provide reason for postponement and new scheduled date if available'
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'scheduled': '#d29922',
            'ongoing': '#2f81f7',
            'completed': '#3fb950',
            'cancelled': '#f85149',
            'postponed': '#a371f7',
        }
        color = colors.get(obj.status, '#8b949e')
        return format_html(
            '<span style="background-color: {}20; color: {}; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def join_link(self, obj):
        if obj.join_url and obj.status not in ['cancelled', 'postponed']:
            return format_html('<a href="{}" target="_blank">Join Meeting</a>', obj.join_url)
        return '-'
    join_link.short_description = 'Join Link'
    
    actions = ['mark_ongoing_selected', 'mark_completed_selected', 'cancel_selected', 'postpone_selected']
    
    def mark_ongoing_selected(self, request, queryset):
        count = 0
        for meeting in queryset:
            if meeting.status == 'scheduled':
                meeting.mark_ongoing()
                count += 1
        self.message_user(request, f'{count} meeting(s) marked as ongoing.')
    mark_ongoing_selected.short_description = 'Mark selected as ongoing'
    
    def mark_completed_selected(self, request, queryset):
        count = 0
        for meeting in queryset:
            if meeting.status in ['scheduled', 'ongoing']:
                meeting.mark_completed()
                count += 1
        self.message_user(request, f'{count} meeting(s) marked as completed.')
    mark_completed_selected.short_description = 'Mark selected as completed'
    
    def cancel_selected(self, request, queryset):
        count = 0
        for meeting in queryset:
            if meeting.status != 'cancelled':
                meeting.cancel()
                count += 1
        self.message_user(request, f'{count} meeting(s) cancelled.')
    cancel_selected.short_description = 'Cancel selected meetings'
    
    def postpone_selected(self, request, queryset):
        count = 0
        for meeting in queryset:
            if meeting.status == 'scheduled':
                meeting.postpone()
                count += 1
        self.message_user(request, f'{count} meeting(s) postponed.')
    postpone_selected.short_description = 'Postpone selected meetings'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'application')