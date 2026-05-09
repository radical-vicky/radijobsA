from django.contrib import admin
from .models import UserWallet, Transaction, WithdrawalRequest

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_earned', 'total_withdrawn', 'updated_at')
    readonly_fields = ('updated_at',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'net_amount', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'net_amount', 'payment_method', 'status', 'requested_at')
    list_filter = ('status', 'payment_method', 'requested_at')
    readonly_fields = ('requested_at',)