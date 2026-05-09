from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('subscribe/', views.initiate_subscription_payment, name='subscribe'),
    path('subscribe-mpesa/', views.subscribe_mpesa, name='subscribe_mpesa'),
    path('mpesa-process/', views.mpesa_process, name='mpesa_process'),  # Add this line
    path('mpesa-status/<int:transaction_id>/', views.mpesa_status, name='mpesa_status'),
    path('bank-instructions/<int:transaction_id>/', views.bank_instructions, name='bank_instructions'),
    path('payment-status/<int:transaction_id>/', views.payment_status, name='payment_status'),
    
    # Webhooks
    path('webhook/binance/', views.binance_webhook, name='binance_webhook'),
    path('webhook/paypal/', views.paypal_webhook, name='paypal_webhook'),
    path('webhook/mpesa/', views.mpesa_webhook, name='mpesa_webhook'),
    
    # Admin
    path('admin/dashboard/', views.payment_dashboard, name='admin_dashboard'),
    path('admin/process-withdrawal/<int:withdrawal_id>/', views.process_withdrawal_payment, name='process_withdrawal'),
]