from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
from decimal import Decimal

from .models import PaymentTransaction, PaymentWebhookLog
from . import mpesa
from subscriptions.models import SubscriptionPayment
from wallet.models import WithdrawalRequest, UserWallet, Transaction
from notifications.models import create_notification


# ==================== SUBSCRIPTION PAYMENTS ====================

@login_required
def initiate_subscription_payment(request):
    """Initiate a subscription payment"""
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = Decimal(settings.SUBSCRIPTION_PRICE_USD)
        
        # Create payment transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            payment_type='subscription',
            payment_method=payment_method,
            amount=amount,
            fee=Decimal(0),
            net_amount=amount,
            transaction_id=str(uuid.uuid4()),
            status='pending'
        )
        
        if payment_method == 'binance':
            from .services import binance_pay
            result = binance_pay.create_order(amount, order_id=transaction.transaction_id)
            if result.get('success'):
                return redirect(result['checkout_url'])
            else:
                transaction.mark_failed(result.get('error', 'Unknown error'))
                messages.error(request, f"Binance Pay error: {result.get('error')}")
                
        elif payment_method == 'paypal':
            from .services import paypal
            result = paypal.create_order(amount)
            if result.get('success'):
                transaction.gateway_transaction_id = result['order_id']
                transaction.save()
                return redirect(result['approval_url'])
            else:
                transaction.mark_failed(result.get('error', 'Unknown error'))
                messages.error(request, f"PayPal error: {result.get('error')}")
                
        elif payment_method == 'mpesa':
            phone_number = request.POST.get('phone_number')
            if not phone_number:
                messages.error(request, "Phone number is required for M-Pesa")
                return redirect('payments:subscribe')
            
            callback_url = request.build_absolute_uri('/payments/webhook/mpesa/')
            result = mpesa.stk_push(
                amount=int(amount),
                phone_number=phone_number,
                account_reference=f"RAD-{transaction.id}",
                transaction_desc="Subscription",
                callback_url=callback_url
            )
            
            if result.get('success'):
                transaction.metadata = {
                    'checkout_request_id': result['checkout_request_id'],
                    'merchant_request_id': result['merchant_request_id'],
                    'phone_number': phone_number
                }
                transaction.status = 'processing'
                transaction.save()
                messages.info(request, "M-Pesa STK Push sent. Please check your phone and enter PIN.")
                return redirect('payments:mpesa_status', transaction_id=transaction.id)
            else:
                transaction.mark_failed(result.get('error', 'Unknown error'))
                messages.error(request, f"M-Pesa error: {result.get('error')}")
        
        elif payment_method == 'bank':
            # Bank transfer - manual approval
            transaction.status = 'processing'
            transaction.save()
            messages.info(request, "Please transfer funds to the bank account below and upload proof of payment.")
            return redirect('payments:bank_instructions', transaction_id=transaction.id)
        
        elif payment_method == 'okx':
            from .services import okx_pay
            result = okx_pay.create_order(amount, order_id=transaction.transaction_id)
            if result.get('success'):
                return redirect(result['checkout_url'])
            else:
                transaction.mark_failed(result.get('error', 'Unknown error'))
                messages.error(request, f"OKX Pay error: {result.get('error')}")
        
        else:
            messages.error(request, "Invalid payment method")
            return redirect('payments:subscribe')
    
    return render(request, 'payments/subscription_payment.html', {
        'amount': settings.SUBSCRIPTION_PRICE_USD,
        'payment_methods': ['binance', 'okx', 'paypal', 'mpesa', 'bank']
    })


@login_required
def subscribe_mpesa(request):
    """Dedicated M-Pesa subscription page"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        amount = Decimal(settings.SUBSCRIPTION_PRICE_USD)
        
        if not phone_number:
            messages.error(request, 'Please enter your M-Pesa phone number')
            return redirect('payments:subscribe_mpesa')
        
        # Create transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            payment_type='subscription',
            payment_method='mpesa',
            amount=amount,
            fee=Decimal(0),
            net_amount=amount,
            currency='KES',
            transaction_id=f"SUB-{uuid.uuid4().hex[:8].upper()}",
            status='pending'
        )
        
        callback_url = request.build_absolute_uri('/payments/webhook/mpesa/')
        result = mpesa.stk_push(
            amount=int(amount),
            phone_number=phone_number,
            account_reference=f"RAD-{transaction.id}",
            transaction_desc="Subscription",
            callback_url=callback_url
        )
        
        if result.get('success'):
            transaction.metadata = {
                'checkout_request_id': result['checkout_request_id'],
                'merchant_request_id': result['merchant_request_id'],
                'phone_number': phone_number
            }
            transaction.status = 'processing'
            transaction.save()
            messages.info(request, "Please check your phone and enter your M-Pesa PIN")
            return redirect('payments:mpesa_status', transaction_id=transaction.id)
        else:
            transaction.status = 'failed'
            transaction.error_message = result.get('error', 'Payment initiation failed')
            transaction.save()
            messages.error(request, f'Payment failed: {result.get("error", "Unknown error")}')
            return redirect('payments:subscribe_mpesa')
    
    context = {
        'subscription_price': getattr(settings, 'SUBSCRIPTION_PRICE_KES', 2000),
    }
    return render(request, 'payments/subscribe_mpesa.html', context)


@login_required
def bank_instructions(request, transaction_id):
    """Show bank transfer instructions"""
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    bank_details = {
        'bank_name': 'Example Bank',
        'account_name': 'RadiloxRemoteJobs Ltd',
        'account_number': '1234567890',
        'swift_code': 'EXMBUS33',
        'routing_number': '021000021'
    }
    
    if request.method == 'POST' and request.FILES.get('proof_of_payment'):
        # Handle proof of payment upload
        proof = request.FILES['proof_of_payment']
        # Save proof to Cloudinary or AWS
        transaction.metadata['proof_of_payment'] = proof.name
        transaction.save()
        messages.success(request, "Proof of payment uploaded. Awaiting admin verification.")
        return redirect('payments:payment_status', transaction_id=transaction.id)
    
    return render(request, 'payments/bank_instructions.html', {
        'transaction': transaction,
        'bank_details': bank_details
    })


@login_required
def payment_status(request, transaction_id):
    """Check payment status"""
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    return render(request, 'payments/payment_status.html', {'transaction': transaction})


@login_required
def mpesa_status(request, transaction_id):
    """Check M-Pesa payment status"""
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    
    # Query status if still processing
    if transaction.status in ['pending', 'processing'] and transaction.metadata.get('checkout_request_id'):
        result = mpesa.query_status(transaction.metadata['checkout_request_id'])
        
        if result.get('success'):
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            # Activate subscription
            transaction.user.has_active_subscription = True
            transaction.user.subscription_started_at = timezone.now()
            transaction.user.subscription_expires_at = timezone.now() + timezone.timedelta(days=30)
            transaction.user.save()
            
            create_notification(
                user=transaction.user,
                notification_type='payment',
                title='Payment Successful',
                message=f'Your payment of KES {transaction.amount} was successful! Your subscription is now active.',
                link='/subscriptions/status/'
            )
            messages.success(request, 'Payment successful! Your subscription is now active.')
        elif result.get('status') == 'cancelled':
            transaction.status = 'cancelled'
            transaction.save()
            messages.warning(request, 'Payment was cancelled.')
    
    return render(request, 'payments/mpesa_status.html', {
        'transaction': transaction,
        'refresh': transaction.status in ['pending', 'processing']
    })


# ==================== WITHDRAWAL PAYMENTS ====================

@login_required
@user_passes_test(lambda u: u.is_admin)
def process_withdrawal_payment(request, withdrawal_id):
    """Admin: Process withdrawal payment through gateway"""
    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id, status='processing')
    
    if request.method == 'POST':
        payment_method = withdrawal.payment_method
        
        if payment_method == 'binance':
            crypto_address = withdrawal.destination_details.get('wallet_address')
            if crypto_address:
                from .services import binance_pay
                result = binance_pay.payout(withdrawal.net_amount, crypto_address)
                
                if result.get('success'):
                    withdrawal.crypto_tx_hash = result.get('tx_hash')
                    withdrawal.status = 'completed'
                    withdrawal.completed_at = timezone.now()
                    withdrawal.save()
                    
                    Transaction.objects.create(
                        user=withdrawal.user,
                        transaction_type='withdrawal',
                        amount=withdrawal.amount,
                        fee=withdrawal.fee,
                        net_amount=withdrawal.net_amount,
                        description=f"Withdrawal via Binance Pay",
                        reference_id=str(withdrawal.id)
                    )
                    
                    create_notification(
                        user=withdrawal.user,
                        notification_type='payment',
                        title='Withdrawal Completed',
                        message=f'Your withdrawal of ${withdrawal.net_amount} has been sent to your Binance wallet.',
                        link='/wallet/'
                    )
                    
                    messages.success(request, f"Withdrawal of ${withdrawal.net_amount} completed!")
                    return redirect('wallet:admin_withdrawals')
                else:
                    messages.error(request, f"Binance payout failed: {result.get('error')}")
        
        elif payment_method == 'paypal':
            email = withdrawal.destination_details.get('email')
            from .services import paypal
            result = paypal.payout(withdrawal.net_amount, email)
            
            if result.get('success'):
                withdrawal.status = 'completed'
                withdrawal.completed_at = timezone.now()
                withdrawal.save()
                
                Transaction.objects.create(
                    user=withdrawal.user,
                    transaction_type='withdrawal',
                    amount=withdrawal.amount,
                    fee=withdrawal.fee,
                    net_amount=withdrawal.net_amount,
                    description=f"Withdrawal via PayPal",
                    reference_id=str(withdrawal.id)
                )
                
                create_notification(
                    user=withdrawal.user,
                    notification_type='payment',
                    title='Withdrawal Completed',
                    message=f'Your withdrawal of ${withdrawal.net_amount} has been sent to your PayPal account.',
                    link='/wallet/'
                )
                
                messages.success(request, f"Withdrawal of ${withdrawal.net_amount} sent to PayPal!")
                return redirect('wallet:admin_withdrawals')
            else:
                messages.error(request, f"PayPal payout failed: {result.get('error')}")
        
        elif payment_method == 'mpesa':
            phone = withdrawal.destination_details.get('phone')
            result = mpesa.b2c_payout(
                amount=int(withdrawal.net_amount),
                phone_number=phone,
                account_reference=f"WDL-{withdrawal.id}",
                transaction_desc="Withdrawal"
            )
            
            if result.get('success'):
                withdrawal.status = 'completed'
                withdrawal.completed_at = timezone.now()
                withdrawal.save()
                
                Transaction.objects.create(
                    user=withdrawal.user,
                    transaction_type='withdrawal',
                    amount=withdrawal.amount,
                    fee=withdrawal.fee,
                    net_amount=withdrawal.net_amount,
                    description=f"Withdrawal via M-Pesa",
                    reference_id=str(withdrawal.id)
                )
                
                create_notification(
                    user=withdrawal.user,
                    notification_type='payment',
                    title='Withdrawal Completed',
                    message=f'Your withdrawal of KES {withdrawal.net_amount} has been sent to your M-Pesa account.',
                    link='/wallet/'
                )
                
                messages.success(request, f"Withdrawal of KES {withdrawal.net_amount} sent to M-Pesa!")
                return redirect('wallet:admin_withdrawals')
            else:
                messages.error(request, f"M-Pesa payout failed: {result.get('error')}")
        
        elif payment_method == 'bank':
            withdrawal.status = 'completed'
            withdrawal.completed_at = timezone.now()
            withdrawal.save()
            
            Transaction.objects.create(
                user=withdrawal.user,
                transaction_type='withdrawal',
                amount=withdrawal.amount,
                fee=withdrawal.fee,
                net_amount=withdrawal.net_amount,
                description=f"Withdrawal via Bank Transfer",
                reference_id=str(withdrawal.id)
            )
            
            create_notification(
                user=withdrawal.user,
                notification_type='payment',
                title='Withdrawal Completed',
                message=f'Your withdrawal of ${withdrawal.net_amount} has been processed via bank transfer.',
                link='/wallet/'
            )
            
            messages.success(request, f"Withdrawal of ${withdrawal.net_amount} marked as completed!")
            return redirect('wallet:admin_withdrawals')
    
    return render(request, 'payments/process_withdrawal.html', {'withdrawal': withdrawal})


# ==================== WEBHOOKS ====================

@csrf_exempt
@require_http_methods(["POST"])
def binance_webhook(request):
    """Handle Binance Pay webhook"""
    try:
        payload = json.loads(request.body)
        
        PaymentWebhookLog.objects.create(
            gateway='binance',
            event_type=payload.get('type', 'unknown'),
            payload=payload,
            processed=False
        )
        
        # Verify signature (implement signature verification)
        
        if payload.get('type') == 'PAYMENT_SUCCESS':
            merchant_trade_no = payload.get('data', {}).get('merchantTradeNo')
            transaction = PaymentTransaction.objects.filter(transaction_id=merchant_trade_no).first()
            
            if transaction and transaction.status in ['pending', 'processing']:
                transaction.mark_completed(
                    gateway_tx_id=payload.get('data', {}).get('transactionId'),
                    tx_hash=payload.get('data', {}).get('crypto', {}).get('txId')
                )
                transaction.user.activate_subscription()
                
                PaymentWebhookLog.objects.filter(payload=payload).update(
                    processed=True,
                    processed_at=timezone.now()
                )
        
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def paypal_webhook(request):
    """Handle PayPal webhook"""
    try:
        payload = json.loads(request.body)
        
        PaymentWebhookLog.objects.create(
            gateway='paypal',
            event_type=payload.get('event_type', 'unknown'),
            payload=payload,
            processed=False
        )
        
        if payload.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':
            order_id = payload.get('resource', {}).get('supplementary_data', {}).get('related_ids', {}).get('order_id')
            transaction = PaymentTransaction.objects.filter(gateway_transaction_id=order_id).first()
            
            if transaction and transaction.status in ['pending', 'processing']:
                transaction.mark_completed(
                    gateway_tx_id=payload.get('resource', {}).get('id')
                )
                transaction.user.activate_subscription()
                
                PaymentWebhookLog.objects.filter(payload=payload).update(
                    processed=True,
                    processed_at=timezone.now()
                )
        
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_webhook(request):
    """Handle M-Pesa webhook callback"""
    try:
        payload = json.loads(request.body)
        
        PaymentWebhookLog.objects.create(
            gateway='mpesa',
            event_type='stk_callback',
            payload=payload,
            processed=False
        )
        
        body = payload.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        
        if result_code == '0':  # Success
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            transaction = PaymentTransaction.objects.filter(
                metadata__checkout_request_id=checkout_request_id
            ).first()
            
            if transaction and transaction.status == 'processing':
                transaction.mark_completed(
                    gateway_tx_id=stk_callback.get('MerchantRequestID')
                )
                transaction.user.activate_subscription()
                
                PaymentWebhookLog.objects.filter(payload=payload).update(
                    processed=True,
                    processed_at=timezone.now()
                )
        
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@user_passes_test(lambda u: u.is_admin)
def payment_dashboard(request):
    """Admin payment analytics dashboard"""
    from django.db.models import Sum, Count
    
    total_revenue = PaymentTransaction.objects.filter(
        payment_type='subscription',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_by_method = PaymentTransaction.objects.filter(
        status='completed'
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    recent_transactions = PaymentTransaction.objects.filter(
        payment_type='subscription'
    ).order_by('-requested_at')[:20]
    
    context = {
        'total_revenue': total_revenue,
        'pending_withdrawals': pending_withdrawals,
        'revenue_by_method': revenue_by_method,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'payments/admin_dashboard.html', context)



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import PaymentTransaction
from . import mpesa
import uuid


@login_required
def mpesa_process(request):
    """Process M-Pesa payment"""
    
    transaction_id = request.session.get('transaction_id')
    phone_number = request.session.get('mpesa_phone')
    
    if not transaction_id or not phone_number:
        messages.error(request, 'Invalid payment session. Please try again.')
        return redirect('subscriptions:subscribe')
    
    transaction = PaymentTransaction.objects.get(id=transaction_id, user=request.user)
    amount = int(transaction.amount)
    
    # Callback URL for M-Pesa
    callback_url = request.build_absolute_uri('/payments/webhook/mpesa/')
    
    # Initiate STK push
    result = mpesa.stk_push(
        amount=amount,
        phone_number=phone_number,
        account_reference=f"RAD-{transaction.id}",
        transaction_desc="Subscription",
        callback_url=callback_url
    )
    
    if result.get('success'):
        transaction.metadata = {
            'checkout_request_id': result['checkout_request_id'],
            'merchant_request_id': result['merchant_request_id'],
            'phone_number': phone_number
        }
        transaction.status = 'processing'
        transaction.save()
        
        messages.success(request, 'STK push sent! Please check your phone and enter your PIN.')
        return redirect('payments:mpesa_status', transaction_id=transaction.id)
    else:
        transaction.status = 'failed'
        transaction.error_message = result.get('error', 'Payment initiation failed')
        transaction.save()
        messages.error(request, f'Payment failed: {result.get("error", "Unknown error")}')
        return redirect('subscriptions:subscribe')