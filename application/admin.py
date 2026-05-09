from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant_name', 'job_title', 'status_badge', 'quiz_score', 'applied_date')
    list_filter = ('status', 'created_at', 'job__job_type')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name', 'job__title')
    readonly_fields = ('created_at', 'updated_at', 'quiz_taken_at')
    
    fieldsets = (
        ('Applicant Information', {
            'fields': ('user', 'full_name', 'email', 'phone_number')
        }),
        ('Job Information', {
            'fields': ('job', 'cover_letter', 'resume', 'portfolio_url', 'linkedin_url')
        }),
        ('Additional Information', {
            'fields': ('years_experience', 'notice_period', 'additional_notes'),
            'classes': ('collapse',)
        }),
        ('Quiz Information', {
            'fields': ('quiz_score', 'quiz_taken_at', 'quiz_expires_at', 'quiz_duration_minutes'),
            'classes': ('collapse',)
        }),
        ('Interview & Onboarding', {
            'fields': ('interview_date', 'interview_zoom_link', 'onboarding_date', 'onboarding_zoom_link'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'hired_at', 'is_active_employment')
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
            'approved': '#2f81f7',
            'interview_scheduled': '#2f81f7',
            'hired': '#3fb950',
            'rejected': '#f85149',
        }
        color = colors.get(obj.status, '#8b949e')
        return format_html(
            '<span style="background-color: {}20; color: {}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def applied_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d')
    applied_date.short_description = 'Applied'
    applied_date.admin_order_field = 'created_at'
    
    actions = ['approve_selected', 'reject_selected']
    
    def approve_selected(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        from notifications.models import create_notification
        
        count = 0
        for obj in queryset:
            if obj.status == 'pending':
                obj.status = 'approved'
                obj.quiz_expires_at = timezone.now() + timedelta(days=7)
                obj.quiz_duration_minutes = 30
                obj.save()
                
                create_notification(
                    user=obj.user,
                    notification_type='quiz',
                    title='Technical Quiz Available',
                    message=f'Your application for {obj.job.title} has been approved! Complete the technical quiz by {obj.quiz_expires_at.strftime("%B %d, %Y at %H:%M")}.',
                    link=f'/quiz/take/{obj.id}/'
                )
                count += 1
        
        self.message_user(request, f'{count} application(s) approved and quiz notifications sent.')
    approve_selected.short_description = 'Approve selected applications'
    
    def reject_selected(self, request, queryset):
        from notifications.models import create_notification
        
        count = 0
        for obj in queryset:
            if obj.status == 'pending':
                obj.status = 'rejected'
                obj.save()
                
                create_notification(
                    user=obj.user,
                    notification_type='application',
                    title='Application Update',
                    message=f'Thank you for applying to {obj.job.title}. After careful review, your application was not selected.',
                    link='/applications/my/'
                )
                count += 1
        
        self.message_user(request, f'{count} application(s) rejected.')
    reject_selected.short_description = 'Reject selected applications'