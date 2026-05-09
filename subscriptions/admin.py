from django.contrib import admin
from .models import SubscriptionPayment

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_method', 'amount_usd', 'status', 'paid_at', 'expires_at')
    list_filter = ('payment_method', 'status', 'paid_at')
    readonly_fields = ('created_at',)