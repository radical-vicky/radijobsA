from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant_name', 'job_title', 'status_badge', 'project_links', 'applied_date')
    list_filter = ('status', 'created_at', 'job__job_type')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name', 'job__title')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at', 'hired_at')
    
    fieldsets = (
        ('Applicant Information', {
            'fields': ('user', 'job', 'cover_letter')
        }),
        ('Project Submission', {
            'fields': ('repository_link', 'deployment_link', 'test_credentials', 'project_notes', 'project_file')
        }),
        ('Status Tracking', {
            'fields': ('status', 'feedback', 'reviewed_by', 'reviewed_at')
        }),
        ('Interview Details', {
            'fields': ('interview_scheduled_at', 'interview_link', 'interview_completed'),
            'classes': ('collapse',)
        }),
        ('Hiring Details', {
            'fields': ('start_date', 'hired_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def applicant_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    applicant_name.short_description = 'Applicant'
    applicant_name.admin_order_field = 'user__first_name'
    
    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#d29922',
            'shortlisted': '#2f81f7',
            'approved': '#2f81f7',
            'interview_scheduled': '#2f81f7',
            'interview_completed': '#2f81f7',
            'hired': '#3fb950',
            'rejected': '#f85149',
        }
        color = colors.get(obj.status, '#8b949e')
        return format_html(
            '<span style="background-color: {}20; color: {}; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def project_links(self, obj):
        links = []
        if obj.repository_link:
            links.append(f'<a href="{obj.repository_link}" target="_blank">Repository</a>')
        if obj.deployment_link:
            links.append(f'<a href="{obj.deployment_link}" target="_blank">Live Demo</a>')
        
        if links:
            # Join with separator and mark as safe HTML
            html_string = ' | '.join(links)
            return mark_safe(html_string)
        return mark_safe('<span class="text-muted">-</span>')
    project_links.short_description = 'Project Links'
    
    def applied_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d')
    applied_date.short_description = 'Applied'
    applied_date.admin_order_field = 'created_at'
    
    actions = ['shortlist_selected', 'approve_selected', 'reject_selected']
    
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
    approve_selected.short_description = 'Approve selected for interview'
    
    def reject_selected(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.status in ['pending', 'shortlisted']:
                obj.reject(request.user, 'Not selected')
                count += 1
        self.message_user(request, f'{count} application(s) rejected.')
    reject_selected.short_description = 'Reject selected applications'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'job', 'reviewed_by')