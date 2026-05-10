from django.contrib import admin
from .models import UserWallet, Transaction, WithdrawalRequest


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance', 'total_earned', 'total_withdrawn', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Wallet Balance', {
            'fields': ('balance', 'total_earned', 'total_withdrawn')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'transaction_type', 'amount', 'net_amount', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'user__username', 'description', 'reference_id')
    readonly_fields = ('created_at',)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'net_amount', 'payment_method', 'status', 'requested_at')
    list_filter = ('status', 'payment_method', 'requested_at')
    search_fields = ('user__email', 'user__username', 'admin_notes')
    readonly_fields = ('requested_at', 'processed_at', 'completed_at')
    
    actions = ['process_selected', 'complete_selected', 'fail_selected']
    
    def process_selected(self, request, queryset):
        count = 0
        for withdrawal in queryset:
            if withdrawal.status == 'pending':
                if withdrawal.process_withdrawal():
                    count += 1
        self.message_user(request, f'{count} withdrawal(s) marked as processing.')
    
    def complete_selected(self, request, queryset):
        count = 0
        for withdrawal in queryset:
            if withdrawal.status == 'processing':
                if withdrawal.complete_withdrawal():
                    count += 1
        self.message_user(request, f'{count} withdrawal(s) marked as completed.')
    
    def fail_selected(self, request, queryset):
        count = 0
        for withdrawal in queryset:
            if withdrawal.status == 'pending':
                if withdrawal.fail_withdrawal('Failed by admin'):
                    count += 1
        self.message_user(request, f'{count} withdrawal(s) marked as failed.')