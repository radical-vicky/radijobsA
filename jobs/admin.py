from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from .models import Job, SavedJob, JobCategory, JobApplication

class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0
    fields = ('application_id', 'status', 'viewed_at')
    readonly_fields = ('application_id', 'viewed_at')
    can_delete = False
    show_change_link = True

class SavedJobInline(admin.TabularInline):
    model = SavedJob
    extra = 0
    fields = ('user', 'saved_at')
    readonly_fields = ('saved_at',)
    can_delete = True

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title_preview', 
        'company_badge', 
        'job_type_badge', 
        'salary_range_display', 
        'status_badge', 
        'featured_badge',
        'applications_count',
        'created_at'
    )
    
    list_filter = (
        'job_type', 
        'experience_level', 
        'is_active', 
        'is_featured',
        'location',
        'created_at'
    )
    
    search_fields = ('title', 'company', 'description', 'requirements', 'skills_required')
    
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'published_at',
        'view_count', 
        'application_count',
        'image_preview',
        'company_logo_preview'
    )
    
    inlines = [JobApplicationInline, SavedJobInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'description', 'requirements', 'project_brief')
        }),
        ('Compensation & Location', {
            'fields': ('salary_range', 'location')
        }),
        ('Classification', {
            'fields': ('job_type', 'experience_level', 'skills_required')
        }),
        ('Images', {
            'fields': ('image', 'image_url', 'image_preview', 'company_logo', 'company_logo_preview'),
            'classes': ('wide',)
        }),
        ('Status & Visibility', {
            'fields': ('is_active', 'is_featured', 'view_count', 'application_count')
        }),
        ('Dates & Expiration', {
            'fields': ('created_at', 'updated_at', 'published_at', 'expires_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'make_active', 
        'make_inactive', 
        'make_featured', 
        'make_unfeatured',
        'extend_expiry_30_days',
        'duplicate_selected_jobs'
    ]
    
    # Custom display methods
    def title_preview(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            obj.title[:50],
            obj.company
        )
    title_preview.short_description = 'Job Title & Company'
    
    def company_badge(self, obj):
        if obj.company_logo:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%; object-fit: cover;" /> {}',
                obj.company_logo.url,
                obj.company
            )
        return obj.company
    company_badge.short_description = 'Company'
    
    def job_type_badge(self, obj):
        colors = {
            'freelance': 'blue',
            'fulltime': 'green',
            'parttime': 'orange',
            'contract': 'purple',
            'internship': 'cyan',
        }
        color = colors.get(obj.job_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_job_type_display()
        )
    job_type_badge.short_description = 'Type'
    
    def salary_range_display(self, obj):
        return format_html('<span style="color: #2ea043;">{}</span>', obj.salary_range)
    salary_range_display.short_description = 'Salary'
    
    def status_badge(self, obj):
        if obj.is_expired:
            return format_html('<span style="background-color: #da3633; color: white; padding: 2px 6px; border-radius: 4px;">Expired</span>')
        elif obj.is_active:
            return format_html('<span style="background-color: #2ea043; color: white; padding: 2px 6px; border-radius: 4px;">Active</span>')
        else:
            return format_html('<span style="background-color: #6e7681; color: white; padding: 2px 6px; border-radius: 4px;">Inactive</span>')
    status_badge.short_description = 'Status'
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="background-color: #f0883e; color: white; padding: 2px 6px; border-radius: 4px;">⭐ Featured</span>')
        return '—'
    featured_badge.short_description = 'Featured'
    
    def applications_count(self, obj):
        count = obj.applications.count()
        if count > 0:
            url = reverse('jobs:applications', args=[obj.id])
            return format_html('<a href="{}" target="_blank" style="color: #2ea043; font-weight: bold;">{} applications</a>', url, count)
        return '0'
    applications_count.short_description = 'Applications'
    
    def image_preview(self, obj):
        if obj.get_image_url:
            return format_html(
                '<img src="{}" width="150" height="100" style="border-radius: 8px; object-fit: cover; border: 1px solid #3d444d;" />',
                obj.get_image_url
            )
        return format_html('<span style="color: #8b949e;">No image uploaded</span>')
    image_preview.short_description = 'Image Preview'
    
    def company_logo_preview(self, obj):
        if obj.get_company_logo_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.get_company_logo_url
            )
        return format_html('<span style="color: #8b949e;">No logo uploaded</span>')
    company_logo_preview.short_description = 'Company Logo'
    
    # Admin actions
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} job(s) marked as active.")
    make_active.short_description = "Mark selected jobs as active"
    
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} job(s) marked as inactive.")
    make_inactive.short_description = "Mark selected jobs as inactive"
    
    def make_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} job(s) marked as featured.")
    make_featured.short_description = "Mark selected jobs as featured"
    
    def make_unfeatured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f"{count} job(s) unmarked as featured.")
    make_unfeatured.short_description = "Remove featured from selected jobs"
    
    def extend_expiry_30_days(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        count = 0
        for job in queryset:
            if job.expires_at:
                job.expires_at += timedelta(days=30)
            else:
                job.expires_at = timezone.now() + timedelta(days=30)
            job.save()
            count += 1
        
        self.message_user(request, f"Expiry date extended by 30 days for {count} job(s).")
    extend_expiry_30_days.short_description = "Extend expiry by 30 days"
    
    def duplicate_selected_jobs(self, request, queryset):
        for job in queryset:
            new_job = Job.objects.create(
                title=f"{job.title} (Copy)",
                company=job.company,
                description=job.description,
                requirements=job.requirements,
                project_brief=job.project_brief,
                salary_range=job.salary_range,
                location=job.location,
                job_type=job.job_type,
                experience_level=job.experience_level,
                skills_required=job.skills_required,
                image=job.image,
                image_url=job.image_url,
                company_logo=job.company_logo,
                created_by=request.user,
                is_active=False
            )
        self.message_user(request, f"{queryset.count()} job(s) duplicated successfully.")
    duplicate_selected_jobs.short_description = "Duplicate selected jobs"
    
    def save_model(self, request, obj, form, change):
        if not change:  # New job
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by').prefetch_related('applications')


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__email', 'job__title')
    readonly_fields = ('saved_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'job')


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'application_id', 'status', 'viewed_at')
    list_filter = ('status', 'viewed_at')
    search_fields = ('job__title', 'application_id')
    readonly_fields = ('application_id', 'viewed_at')
    
    actions = ['mark_as_viewed', 'mark_as_shortlisted', 'mark_as_rejected']
    
    def mark_as_viewed(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='viewed', viewed_at=timezone.now())
        self.message_user(request, f"{count} application(s) marked as viewed.")
    mark_as_viewed.short_description = "Mark as viewed"
    
    def mark_as_shortlisted(self, request, queryset):
        count = queryset.update(status='shortlisted')
        self.message_user(request, f"{count} application(s) shortlisted.")
    mark_as_shortlisted.short_description = "Mark as shortlisted"
    
    def mark_as_rejected(self, request, queryset):
        count = queryset.update(status='rejected')
        self.message_user(request, f"{count} application(s) rejected.")
    mark_as_rejected.short_description = "Mark as rejected"