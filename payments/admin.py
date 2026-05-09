from django.contrib import admin
from .models import PaymentTransaction, PaymentWebhookLog

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'payment_type', 'payment_method', 'amount', 'status', 'requested_at')
    list_filter = ('payment_type', 'payment_method', 'status', 'requested_at')
    search_fields = ('user__email', 'transaction_id', 'gateway_transaction_id')
    readonly_fields = ('requested_at', 'processed_at', 'completed_at')
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'payment_method', 'amount', 'fee', 'net_amount', 'currency')
        }),
        ('Crypto Details', {
            'fields': ('crypto_amount', 'crypto_currency', 'crypto_address', 'crypto_tx_hash'),
            'classes': ('collapse',)
        }),
        ('Transaction IDs', {
            'fields': ('transaction_id', 'gateway_transaction_id')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'processed_at', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('metadata', 'webhook_payload'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('gateway', 'event_type', 'processed', 'created_at')
    list_filter = ('gateway', 'processed', 'created_at')
    readonly_fields = ('created_at',)