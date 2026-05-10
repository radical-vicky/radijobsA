from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from .models import Task, TaskAttachment, TaskComment


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1
    fields = ('file', 'filename', 'uploaded_by')
    readonly_fields = ('uploaded_at',)


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 1
    fields = ('user', 'comment', 'is_admin_note')
    readonly_fields = ('created_at',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_preview', 'task_title', 'assigned_to_user', 'status_badge', 'budget_amount', 'deadline', 'assigned_at')
    list_filter = ('status', 'assigned_at', 'deadline', 'job')
    search_fields = ('title', 'description', 'assigned_to__email', 'assigned_to__username')
    readonly_fields = ('assigned_at', 'started_at', 'submitted_at', 'approved_at', 'paid_at', 'created_at', 'updated_at')
    actions = ['approve_selected', 'pay_selected_working', 'request_revision_selected']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('job', 'title', 'description', 'budget_amount')
        }),
        ('Task Image', {
            'fields': ('image', 'image_url'),
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_by', 'deadline')
        }),
        ('Status & Dates', {
            'fields': ('status', 'assigned_at', 'started_at', 'submitted_at', 'approved_at', 'paid_at')
        }),
        ('Submission', {
            'fields': ('submission_url', 'submission_notes'),
            'classes': ('collapse',)
        }),
        ('Revisions', {
            'fields': ('revision_feedback', 'revision_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [TaskAttachmentInline, TaskCommentInline]
    
    def task_title(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    task_title.short_description = 'Title'
    
    def assigned_to_user(self, obj):
        user = obj.assigned_to
        return format_html(
            '<a href="{}" style="color: #2f81f7;">{}</a>',
            reverse('admin:accounts_user_change', args=[user.id]),
            user.email
        )
    assigned_to_user.short_description = 'Assigned To'
    
    def status_badge(self, obj):
        colors = {
            'assigned': '#d29922',
            'in_progress': '#2f81f7',
            'submitted': '#a371f7',
            'approved': '#3fb950',
            'paid': '#3fb950',
            'rejected': '#f85149',
            'revision_requested': '#d29922',
        }
        color = colors.get(obj.status, '#8b949e')
        return format_html(
            '<span style="background-color: {}20; color: {}; padding: 4px 8px; font-size: 11px; font-weight: 500;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def task_preview(self, obj):
        image_url = obj.get_image_url()
        if image_url:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border: 1px solid #2d2f36;" />',
                image_url
            )
        return format_html(
            '<div style="width: 40px; height: 40px; background: #0d1117; border: 1px solid #2d2f36; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 600; color: #2f81f7;">{}</div>',
            obj.title[:1].upper() if obj.title else '?'
        )
    task_preview.short_description = 'Image'
    
    def approve_selected(self, request, queryset):
        count = 0
        for task in queryset:
            if task.status == 'submitted':
                task.approve_task()
                count += 1
        self.message_user(request, f'{count} task(s) approved.')
    approve_selected.short_description = 'Approve selected tasks'
    
    def pay_selected_working(self, request, queryset):
        """PAY SELECTED TASKS - Creates transaction and sends notification"""
        from wallet.models import UserWallet, Transaction
        from notifications.models import Notification
        from django.core.mail import send_mail
        from django.conf import settings
        
        count = 0
        for task in queryset:
            if task.status == 'approved':
                try:
                    amount = Decimal(str(task.budget_amount))
                    
                    # Get or create wallet
                    wallet, created = UserWallet.objects.get_or_create(user=task.assigned_to)
                    
                    # Update wallet balance
                    wallet.balance += amount
                    wallet.total_earned += amount
                    wallet.save()
                    
                    # Create transaction
                    Transaction.objects.create(
                        user=task.assigned_to,
                        transaction_type='task_payment',
                        amount=amount,
                        fee=0,
                        net_amount=amount,
                        description=f"Payment for task: {task.title} (Job: {task.job.title})",
                        reference_id=str(task.id)
                    )
                    
                    # Mark task as paid
                    task.status = 'paid'
                    task.paid_at = timezone.now()
                    task.save()
                    
                    # Send in-app notification
                    Notification.objects.create(
                        user=task.assigned_to,
                        notification_type='payment',
                        title='Payment Received',
                        message=f"${amount} has been added to your wallet for task: {task.title}. New balance: ${wallet.balance}",
                        link='/wallet/',
                        status='unread'
                    )
                    
                    # Send email notification
                    send_mail(
                        subject=f"Payment Received - {task.title}",
                        message=f"""
Dear {task.assigned_to.get_full_name() or task.assigned_to.username},

You have received a payment of ${amount} for task: {task.title}

Current Wallet Balance: ${wallet.balance}

View your wallet: http://127.0.0.1:8000/wallet/

Thank you for your hard work!

Best regards,
RadiloxRemoteJobs Team
""",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[task.assigned_to.email],
                        fail_silently=False
                    )
                    
                    count += 1
                    self.message_user(request, f'✓ Paid: {task.title} - ${amount}')
                    
                except Exception as e:
                    self.message_user(request, f'✗ Error paying {task.title}: {str(e)}')
        
        self.message_user(request, f'Successfully paid {count} task(s). Wallet updated, transactions created, and notifications sent.')
    pay_selected_working.short_description = '💰 PAY SELECTED TASKS (Auto-update wallet)'
    
    def request_revision_selected(self, request, queryset):
        count = 0
        for task in queryset:
            if task.status == 'submitted':
                task.request_revision('Revision requested by admin')
                count += 1
        self.message_user(request, f'{count} task(s) sent for revision.')
    request_revision_selected.short_description = 'Request revision for selected tasks'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_link', 'filename', 'uploaded_by_user', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('filename', 'task__title', 'uploaded_by__email')
    readonly_fields = ('uploaded_at',)
    
    def task_link(self, obj):
        return format_html(
            '<a href="{}" style="color: #2f81f7;">{}</a>',
            reverse('admin:tasks_task_change', args=[obj.task.id]),
            obj.task.title[:50]
        )
    task_link.short_description = 'Task'
    
    def uploaded_by_user(self, obj):
        return obj.uploaded_by.email
    uploaded_by_user.short_description = 'Uploaded By'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_link', 'user_email', 'comment_preview', 'is_admin_note', 'created_at')
    list_filter = ('is_admin_note', 'created_at')
    search_fields = ('comment', 'task__title', 'user__email')
    readonly_fields = ('created_at',)
    
    def task_link(self, obj):
        return format_html(
            '<a href="{}" style="color: #2f81f7;">{}</a>',
            reverse('admin:tasks_task_change', args=[obj.task.id]),
            obj.task.title[:50]
        )
    task_link.short_description = 'Task'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def comment_preview(self, obj):
        comment = obj.comment[:60] + '...' if len(obj.comment) > 60 else obj.comment
        return comment
    comment_preview.short_description = 'Comment'