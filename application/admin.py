from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Application
from notifications.models import create_notification


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant_name', 'job_title', 'status_badge', 'applied_date', 'repository_link_preview')
    list_filter = ('status', 'created_at', 'job__job_type')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name', 'job__title')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at', 'repository_link')
    
    fieldsets = (
        ('Applicant Information', {
            'fields': ('user',)
        }),
        ('Application Details', {
            'fields': ('job', 'cover_letter', 'repository_link', 'deployment_link', 'test_credentials', 'project_notes', 'project_file')
        }),
        ('Status', {
            'fields': ('status', 'feedback', 'reviewed_by', 'reviewed_at')
        }),
        ('Interview', {
            'fields': ('interview_scheduled_at', 'interview_link', 'interview_completed'),
            'classes': ('collapse',)
        }),
        ('Hiring', {
            'fields': ('hired_at', 'start_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def applicant_name(self, obj):
        if obj.user.get_full_name():
            return obj.user.get_full_name()
        return obj.user.username
    applicant_name.short_description = 'Applicant'
    applicant_name.admin_order_field = 'user__first_name'
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'
    job_title.admin_order_field = 'job__title'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#d29922',
            'shortlisted': '#2f81f7',
            'approved': '#2f81f7',
            'interview_scheduled': '#a371f7',
            'interview_completed': '#3fb950',
            'hired': '#3fb950',
            'rejected': '#f85149',
        }
        color = colors.get(obj.status, '#8b949e')
        return format_html(
            '<span style="background-color: {}20; color: {}; padding: 4px 8px; font-size: 11px; font-weight: 500;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def applied_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d')
    applied_date.short_description = 'Applied'
    applied_date.admin_order_field = 'created_at'
    
    def repository_link_preview(self, obj):
        if obj.repository_link:
            return format_html('<a href="{}" target="_blank" style="color: #2f81f7;">View Repo</a>', obj.repository_link)
        return '-'
    repository_link_preview.short_description = 'Repository'
    
    actions = ['shortlist_selected', 'approve_selected', 'reject_selected', 'hire_selected']
    
    def shortlist_selected(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.status == 'pending':
                obj.shortlist(request.user)
                count += 1
        self.message_user(request, f'{count} application(s) shortlisted.')
    shortlist_selected.short_description = 'Shortlist selected applications'
    
    def approve_selected(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.status == 'shortlisted':
                obj.approve_for_interview(request.user)
                count += 1
        self.message_user(request, f'{count} application(s) approved for interview.')
    approve_selected.short_description = 'Approve for interview'
    
    def reject_selected(self, request, queryset):
        count = 0
        feedback = "Not selected at this time"
        for obj in queryset:
            if obj.status != 'hired':
                obj.reject(request.user, feedback)
                count += 1
        self.message_user(request, f'{count} application(s) rejected.')
    reject_selected.short_description = 'Reject selected applications'
    
    def hire_selected(self, request, queryset):
        from django.utils import timezone
        count = 0
        for obj in queryset:
            if obj.status == 'interview_completed':
                obj.hire(timezone.now().date())
                count += 1
        self.message_user(request, f'{count} applicant(s) hired.')
    hire_selected.short_description = 'Hire selected applicants'