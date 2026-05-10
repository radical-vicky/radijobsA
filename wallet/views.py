from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum  # Add this import
from decimal import Decimal
from .models import UserWallet, Transaction, WithdrawalRequest
from notifications.models import Notification
from accounts.models import User


@login_required
def wallet_dashboard(request):
    """Main wallet dashboard"""
    wallet, created = UserWallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:15]
    
    # Calculate stats - use Sum directly, not models.Sum
    total_withdrawn = WithdrawalRequest.objects.filter(user=request.user, status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_withdrawals = WithdrawalRequest.objects.filter(user=request.user, status='pending').count()
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'total_withdrawn': total_withdrawn,
        'pending_withdrawals': pending_withdrawals,
    }
    return render(request, 'wallet/dashboard.html', context)


@login_required
def withdrawal_request(request):
    """Request withdrawal"""
    wallet, created = UserWallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method')
        
        # Validate amount
        if amount < settings.MINIMUM_WITHDRAWAL_USD:
            messages.error(request, f"Minimum withdrawal is ${settings.MINIMUM_WITHDRAWAL_USD}")
            return redirect('wallet:withdrawal_request')
        
        if amount > wallet.balance:
            messages.error(request, "Insufficient balance")
            return redirect('wallet:withdrawal_request')
        
        if amount > settings.MAX_WITHDRAWAL_USD:
            messages.error(request, f"Maximum withdrawal is ${settings.MAX_WITHDRAWAL_USD}")
            return redirect('wallet:withdrawal_request')
        
        # Calculate fee
        fee = amount * (Decimal(settings.WITHDRAWAL_FEE_PERCENTAGE) / 100)
        net_amount = amount - fee
        
        # Get payment method details from user's saved payment methods
        payment_method_obj = request.user.payment_methods.filter(payment_type=payment_method, is_default=True).first()
        
        if not payment_method_obj:
            messages.error(request, "Please add a payment method first")
            return redirect('accounts:payment_methods')
        
        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            user=request.user,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            payment_method=payment_method,
            destination_details={
                'email': getattr(payment_method_obj, 'account_email', ''),
                'phone': getattr(payment_method_obj, 'phone_number', ''),
                'bank_name': getattr(payment_method_obj, 'bank_name', ''),
                'account_name': getattr(payment_method_obj, 'bank_account_name', ''),
                'account_number': getattr(payment_method_obj, 'bank_account_number', ''),
            },
            status='pending'
        )
        
        messages.success(request, f"Withdrawal request of ${amount} submitted for approval.")
        
        # Notify admin
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                notification_type='withdrawal',
                title='New Withdrawal Request',
                message=f"{request.user.username} requested withdrawal of ${amount}",
                link='/admin/wallet/withdrawalrequest/',
                status='unread'
            )
        
        return redirect('wallet:withdrawal_history')
    
    context = {
        'wallet': wallet,
        'min_amount': settings.MINIMUM_WITHDRAWAL_USD,
        'max_amount': settings.MAX_WITHDRAWAL_USD,
        'fee_percentage': settings.WITHDRAWAL_FEE_PERCENTAGE,
    }
    return render(request, 'wallet/withdrawal_request.html', context)


@login_required
def withdrawal_history(request):
    """View withdrawal history"""
    withdrawals = WithdrawalRequest.objects.filter(user=request.user).order_by('-requested_at')
    
    # Calculate summary
    total_withdrawn = withdrawals.filter(status='completed').aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    pending_total = withdrawals.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    completed_count = withdrawals.filter(status='completed').count()
    
    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wallet/withdrawal_history.html', {
        'withdrawals': page_obj,
        'total_withdrawn': total_withdrawn,
        'pending_total': pending_total,
        'completed_count': completed_count,
    })

@login_required
def transaction_history(request):
    """View all transactions with summary"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate summary
    total_deposits = transactions.filter(transaction_type='deposit').aggregate(Sum('amount'))['amount__sum'] or 0
    total_withdrawals = transactions.filter(transaction_type='withdrawal').aggregate(Sum('amount'))['amount__sum'] or 0
    total_task_payments = transactions.filter(transaction_type='task_payment').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transactions': page_obj,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_task_payments': total_task_payments,
    }
    return render(request, 'wallet/transaction_history.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_withdrawals(request):
    """Admin view all withdrawal requests"""
    withdrawals = WithdrawalRequest.objects.all().order_by('-requested_at')
    pending = withdrawals.filter(status='pending')
    
    if request.method == 'POST':
        withdrawal_id = request.POST.get('withdrawal_id')
        action = request.POST.get('action')
        withdrawal = get_object_or_404(WithdrawalRequest, pk=withdrawal_id)
        
        if action == 'process':
            if withdrawal.process_withdrawal():
                messages.success(request, f"Withdrawal #{withdrawal.id} is being processed.")
            else:
                messages.error(request, f"Failed to process withdrawal #{withdrawal.id}")
        
        elif action == 'complete':
            if withdrawal.complete_withdrawal():
                messages.success(request, f"Withdrawal #{withdrawal.id} completed.")
            else:
                messages.error(request, f"Failed to complete withdrawal #{withdrawal.id}")
        
        elif action == 'fail':
            reason = request.POST.get('reason', '')
            if withdrawal.fail_withdrawal(reason):
                messages.error(request, f"Withdrawal #{withdrawal.id} marked as failed.")
        
        return redirect('wallet:admin_withdrawals')
    
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wallet/admin_withdrawals.html', {
        'withdrawals': page_obj,
        'pending_count': pending.count(),
    })