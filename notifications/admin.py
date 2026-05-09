from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title_preview', 'notification_type', 'status', 'created_at')
    list_filter = ('notification_type', 'status', 'created_at')
    search_fields = ('user__email', 'user__username', 'title', 'message')
    readonly_fields = ('created_at', 'read_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'notification_type')
        }),
        ('Content', {
            'fields': ('title', 'message', 'link')
        }),
        ('Status', {
            'fields': ('status', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'archive_selected']
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def mark_as_read(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.mark_as_read():
                count += 1
        self.message_user(request, f"{count} notification(s) marked as read.")
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.mark_as_unread():
                count += 1
        self.message_user(request, f"{count} notification(s) marked as unread.")
    mark_as_unread.short_description = "Mark selected as unread"
    
    def archive_selected(self, request, queryset):
        count = queryset.update(status='archived')
        self.message_user(request, f"{count} notification(s) archived.")
    archive_selected.short_description = "Archive selected"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email', 'user__username')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': ('email_on_application', 'email_on_quiz', 'email_on_task', 
                      'email_on_payment', 'email_on_subscription', 'email_on_interview',
                      'email_on_withdrawal')
        }),
        ('In-App Notifications', {
            'fields': ('in_app_on_application', 'in_app_on_quiz', 'in_app_on_task',
                      'in_app_on_payment', 'in_app_on_subscription', 'in_app_on_interview',
                      'in_app_on_withdrawal')
        }),
    )