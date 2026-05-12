from django.contrib import admin
from django.utils.html import format_html
from .models import Subscription, SubscriptionPayment


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'is_active', 'start_date', 'end_date', 'days_remaining')
    list_filter = ('plan', 'is_active', 'start_date')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Plan Details', {
            'fields': ('plan', 'is_active')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def days_remaining(self, obj):
        if obj.end_date:
            from django.utils import timezone
            delta = obj.end_date - timezone.now()
            days = max(0, delta.days)
            return f"{days} days"
        return '-'
    days_remaining.short_description = 'Days Remaining'


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'payment_method', 'status', 'created_at', 'payment_link')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('user__email', 'user__username', 'transaction_id')
    readonly_fields = ('created_at', 'paid_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'amount', 'crypto_currency', 'crypto_amount')
        }),
        ('Transaction Information', {
            'fields': ('transaction_id', 'status', 'metadata')
        }),
        ('Dates', {
            'fields': ('created_at', 'paid_at')
        }),
    )
    
    def payment_link(self, obj):
        if obj.payment_method == 'mpesa' and obj.transaction_id:
            return format_html('<span style="color: #2f81f7;">{}</span>', obj.transaction_id[:20])
        return '-'
    payment_link.short_description = 'Reference'
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        count = 0
        for payment in queryset:
            if payment.status != 'completed':
                payment.status = 'completed'
                payment.paid_at = timezone.now()
                payment.save()
                
                # Create or update subscription
                subscription, created = Subscription.objects.update_or_create(
                    user=payment.user,
                    defaults={
                        'plan': 'pro',
                        'is_active': True,
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=30),
                    }
                )
                
                # Update user model
                payment.user.has_active_subscription = True
                payment.user.subscription_expires_at = timezone.now() + timedelta(days=30)
                payment.user.save()
                
                count += 1
                
        self.message_user(request, f'{count} payment(s) marked as completed and subscription activated.')
    mark_as_completed.short_description = 'Mark selected as completed (activate subscription)'
    
    def mark_as_failed(self, request, queryset):
        count = queryset.update(status='failed')
        self.message_user(request, f'{count} payment(s) marked as failed.')
    mark_as_failed.short_description = 'Mark selected as failed'