from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from .models import UserWallet, Transaction, WithdrawalRequest


@login_required
def wallet_dashboard(request):
    wallet, created = UserWallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet/dashboard.html', context)


@login_required
def withdrawal_request(request):
    wallet = get_object_or_404(UserWallet, user=request.user)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method')
        
        if amount < settings.MINIMUM_WITHDRAWAL_USD:
            messages.error(request, f"Minimum withdrawal is ${settings.MINIMUM_WITHDRAWAL_USD}")
            return redirect('wallet:withdrawal_request')
        
        if amount > wallet.balance:
            messages.error(request, "Insufficient balance")
            return redirect('wallet:withdrawal_request')
        
        if amount > settings.MAX_WITHDRAWAL_USD:
            messages.error(request, f"Maximum withdrawal is ${settings.MAX_WITHDRAWAL_USD}")
            return redirect('wallet:withdrawal_request')
        
        fee = amount * (Decimal(settings.WITHDRAWAL_FEE_PERCENTAGE) / 100)
        net_amount = amount - fee
        
        destination_details = {}
        
        # Fix: Use 'payment_type' not 'method_type'
        user_payment_methods = request.user.payment_methods.filter(payment_type=payment_method, is_default=True)
        
        if user_payment_methods.exists():
            pm = user_payment_methods.first()
            if payment_method == 'paypal':
                destination_details['email'] = pm.account_email
            elif payment_method == 'mpesa':
                destination_details['phone'] = pm.phone_number
            elif payment_method == 'bank_account' or payment_method == 'bank':
                destination_details.update({
                    'bank_name': pm.bank_name,
                    'account_name': pm.bank_account_name,
                    'account_number': pm.bank_account_number,
                    'swift_code': pm.bank_swift_code,
                })
        
        withdrawal = WithdrawalRequest.objects.create(
            user=request.user,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            payment_method=payment_method,
            destination_details=destination_details,
            status='pending'
        )
        
        messages.success(request, f"Withdrawal request submitted for ${amount}. Fee: ${fee}. You'll receive ${net_amount}.")
        return redirect('wallet:withdrawal_history')
    
    # Get user's payment methods for the form
    payment_methods = request.user.payment_methods.filter(is_active=True)
    
    context = {
        'wallet': wallet,
        'min_amount': settings.MINIMUM_WITHDRAWAL_USD,
        'max_amount': settings.MAX_WITHDRAWAL_USD,
        'fee_percentage': settings.WITHDRAWAL_FEE_PERCENTAGE,
        'payment_methods': payment_methods,
    }
    return render(request, 'wallet/withdrawal_request.html', context)


@login_required
def withdrawal_history(request):
    withdrawals = WithdrawalRequest.objects.filter(user=request.user).order_by('-requested_at')
    
    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wallet/withdrawal_history.html', {'withdrawals': page_obj})


@login_required
def transaction_history(request):
    """View all transactions"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transactions': page_obj,
    }
    return render(request, 'wallet/transaction_history.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_withdrawals(request):
    withdrawals = WithdrawalRequest.objects.all().order_by('-requested_at')
    pending = withdrawals.filter(status='pending')
    
    if request.method == 'POST':
        withdrawal_id = request.POST.get('withdrawal_id')
        action = request.POST.get('action')
        withdrawal = get_object_or_404(WithdrawalRequest, pk=withdrawal_id)
        
        if action == 'approve':
            withdrawal.status = 'processing'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            messages.success(request, f"Withdrawal #{withdrawal.id} marked as processing.")
        elif action == 'complete':
            withdrawal.status = 'completed'
            withdrawal.completed_at = timezone.now()
            withdrawal.save()
            
            # Update wallet
            wallet = withdrawal.user.wallet
            wallet.balance -= withdrawal.amount
            wallet.total_withdrawn += withdrawal.net_amount
            wallet.save()
            
            Transaction.objects.create(
                user=withdrawal.user,
                transaction_type='debit',
                amount=withdrawal.amount,
                fee=withdrawal.fee,
                net_amount=withdrawal.net_amount,
                description=f"Withdrawal via {withdrawal.payment_method}",
                reference_id=str(withdrawal.id)
            )
            messages.success(request, f"Withdrawal #{withdrawal.id} completed.")
        elif action == 'fail':
            withdrawal.status = 'failed'
            withdrawal.save()
            messages.warning(request, f"Withdrawal #{withdrawal.id} marked as failed.")
    
    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wallet/admin_withdrawals.html', {
        'withdrawals': page_obj,
        'pending_count': pending.count(),
    })