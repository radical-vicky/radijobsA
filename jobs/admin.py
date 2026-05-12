from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Job, SavedJob, JobCategory


class SavedJobInline(admin.TabularInline):
    model = SavedJob
    extra = 0
    fields = ('user', 'saved_at')
    readonly_fields = ('saved_at',)
    can_delete = True


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'company', 'job_type', 'is_active', 'is_featured', 'application_deadline_display', 'application_count', 'created_at')
    list_filter = ('job_type', 'experience_level', 'is_active', 'is_featured', 'created_at')
    search_fields = ('title', 'company', 'description', 'skills_required')
    list_editable = ('is_active', 'is_featured')
    
    readonly_fields = ('created_at', 'updated_at', 'view_count', 'application_count', 'image_preview_large')
    
    inlines = [SavedJobInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'description', 'requirements', 'project_brief')
        }),
        ('Categories', {
            'fields': ('categories',),
            'classes': ('wide',)
        }),
        ('Compensation & Location', {
            'fields': ('salary_range', 'location')
        }),
        ('Classification', {
            'fields': ('job_type', 'experience_level', 'skills_required')
        }),
        ('Images', {
            'fields': ('image', 'image_url', 'image_preview_large', 'company_logo'),
            'classes': ('wide',)
        }),
        ('Deadlines', {
            'fields': ('application_deadline', 'expires_at'),
            'classes': ('wide',),
            'description': 'Set application deadline to control when applications close.'
        }),
        ('Status & Visibility', {
            'fields': ('is_active', 'is_featured', 'view_count', 'application_count')
        }),
        ('Created By', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'make_featured', 'reset_view_count', 'set_deadline_7_days', 'set_deadline_14_days', 'set_deadline_30_days']
    
    def image_preview(self, obj):
        image_url = obj.get_image_url
        if image_url:
            return format_html('<img src="{}" width="40" height="40" style="object-fit: cover;" />', image_url)
        return '-'
    image_preview.short_description = 'Image'
    
    def image_preview_large(self, obj):
        image_url = obj.get_image_url
        if image_url:
            return format_html(
                '<div style="background: #0d1117; padding: 12px; border: 1px solid #30363d; display: inline-block;">'
                '<img src="{}" width="200" height="120" style="object-fit: cover;" />'
                '</div>',
                image_url
            )
        return '<div style="background: #0d1117; padding: 12px; border: 1px solid #30363d; color: #8b949e;">No image uploaded</div>'
    image_preview_large.short_description = 'Image Preview'
    
    def application_deadline_display(self, obj):
        if obj.application_deadline:
            if obj.is_application_deadline_passed:
                return format_html(
                    '<span style="background-color: #da3633; color: white; padding: 4px 8px;">Expired</span><br><small>{}</small>',
                    obj.application_deadline.strftime("%Y-%m-%d %H:%M")
                )
            else:
                delta = obj.application_deadline_remaining
                if delta:
                    days = delta.days
                    hours = delta.seconds // 3600
                    return format_html(
                        '<span style="background-color: #2ea043; color: white; padding: 4px 8px;">Open</span><br><small>{}d {}h left</small>',
                        days, hours
                    )
        return '-'
    application_deadline_display.short_description = 'Deadline'
    
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} job(s) marked as active.")
    make_active.short_description = "Mark as active"
    
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} job(s) marked as inactive.")
    make_inactive.short_description = "Mark as inactive"
    
    def make_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} job(s) marked as featured.")
    make_featured.short_description = "Mark as featured"
    
    def reset_view_count(self, request, queryset):
        count = queryset.update(view_count=0)
        self.message_user(request, f"View count reset for {count} job(s).")
    reset_view_count.short_description = "Reset view count"
    
    def set_deadline_7_days(self, request, queryset):
        from datetime import timedelta
        deadline = timezone.now() + timedelta(days=7)
        count = queryset.update(application_deadline=deadline)
        self.message_user(request, f"Application deadline set to 7 days from now for {count} job(s).")
    set_deadline_7_days.short_description = "Set deadline +7 days"
    
    def set_deadline_14_days(self, request, queryset):
        from datetime import timedelta
        deadline = timezone.now() + timedelta(days=14)
        count = queryset.update(application_deadline=deadline)
        self.message_user(request, f"Application deadline set to 14 days from now for {count} job(s).")
    set_deadline_14_days.short_description = "Set deadline +14 days"
    
    def set_deadline_30_days(self, request, queryset):
        from datetime import timedelta
        deadline = timezone.now() + timedelta(days=30)
        count = queryset.update(application_deadline=deadline)
        self.message_user(request, f"Application deadline set to 30 days from now for {count} job(s).")
    set_deadline_30_days.short_description = "Set deadline +30 days"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__email', 'user__username', 'job__title')
    readonly_fields = ('saved_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'job')


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order', 'is_active')