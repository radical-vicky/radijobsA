from django.contrib import admin
from .models import Task, TaskAttachment, TaskComment

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'job', 'budget_amount', 'status', 'deadline', 'created_at')
    list_filter = ('status', 'job', 'created_at')
    search_fields = ('title', 'description', 'assigned_to__email', 'assigned_to__username')
    readonly_fields = ('assigned_at', 'started_at', 'submitted_at', 'approved_at', 'paid_at', 'created_at', 'updated_at')
    inlines = [TaskAttachmentInline, TaskCommentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'job', 'assigned_to', 'assigned_by', 'budget_amount')
        }),
        ('Status & Dates', {
            'fields': ('status', 'deadline', 'assigned_at', 'started_at', 'submitted_at', 'approved_at', 'paid_at')
        }),
        ('Submission', {
            'fields': ('submission_url', 'submission_notes')
        }),
        ('Revisions', {
            'fields': ('revision_feedback', 'revision_count')
        }),
    )

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'filename', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'comment_preview', 'created_at')
    list_filter = ('created_at',)
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'