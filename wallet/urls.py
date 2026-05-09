from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    # Main wallet
    path('', views.wallet_dashboard, name='dashboard'),
    path('dashboard/', views.wallet_dashboard, name='dashboard'),
    
    # Withdrawals
    path('withdraw/', views.withdrawal_request, name='withdrawal_request'),
    path('withdrawal-history/', views.withdrawal_history, name='withdrawal_history'),
    
    # Transactions
    path('transactions/', views.transaction_history, name='transaction_history'),
    
    # Admin
    path('admin/withdrawals/', views.admin_withdrawals, name='admin_withdrawals'),
]